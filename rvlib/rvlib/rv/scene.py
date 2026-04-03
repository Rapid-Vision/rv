from abc import ABC, abstractmethod
import json
import math
import os
import pathlib
import random
import uuid
from mathutils import Vector
from typing import Literal, Optional, Union

import bpy
import mathutils

from .assets import (
    _combine_arglist_set,
    _estimate_loader_radius,
    _load_all_objects,
    _load_single_object,
    _remove_blender_object,
)
from .compositor import _configure_compositor
from .geometry import (
    _aabb_from_points,
    _convex_hull_2d,
    _convex_hull_planes,
    _distance_to_polygon_edges,
    _get_object_world_vertices,
    _mesh_object_overlaps_any,
    _object_world_radius,
    _point_in_convex_polygon,
    _points_centroid,
    _polygon_signed_area,
    _random_unit_vector,
    _sample_convex_polygon,
    _sample_rotation_quaternion,
)
from .material import BasicMaterial, ImportedMaterial, _normalize_semantic_channel
from .object import (
    AreaLight,
    Camera,
    Object,
    ObjectLoader,
    ObjectStats,
    ParametricSource,
    PointLight,
    SpotLight,
    SunLight,
    _Serializable,
)
from .passes import RenderPass
from .render import (
    _configure_passes,
    _deselect,
    _set_resolution,
    _set_time_limit,
    _use_cycles,
    _use_gpu,
)
from .scatter import (
    _ensure_positive_tuple,
    _finalize_scatter_stats,
    _init_scatter_stats,
    _overlaps_by_radius,
    _validate_scatter_common,
)
from .types import (
    AABB,
    CellCoords,
    Float2,
    Float3,
    ObjectLoaderSource,
    RenderPassSet,
    Resolution,
    SemanticChannelSet,
    TagSet,
)
from .utils import (
    _get_generated_collection,
    _mark_object_tree,
    _move_object_to_generated_collection,
)


class Domain:
    """
    Scatter domain descriptor used by scene scattering methods.
    """

    kind: str
    data: dict
    dimension: int

    def __init__(self, kind: str, data: dict, dimension: int):
        self.kind = kind
        self.data = data
        self.dimension = dimension

    def inset(self, margin: float) -> "Domain":
        margin = float(margin)
        if margin < 0:
            raise ValueError("margin must be >= 0.")

        data = dict(self.data)
        data["inset_margin"] = float(data.get("inset_margin", 0.0)) + margin
        return Domain(self.kind, data, self.dimension)

    def _effective_inset_margin(self) -> float:
        return float(self.data.get("inset_margin", 0.0))

    @staticmethod
    def rect(center: Float2 = (0.0, 0.0), size: Float2 = (10.0, 10.0), z: float = 0.0) -> "Domain":
        _ensure_positive_tuple(size, 2, "size")
        return Domain("rect", {"center": tuple(center), "size": tuple(size), "z": z}, 2)

    @staticmethod
    def ellipse(
        center: Float2 = (0.0, 0.0),
        radii: Float2 = (5.0, 3.0),
        z: float = 0.0,
    ) -> "Domain":
        _ensure_positive_tuple(radii, 2, "radii")
        return Domain("ellipse", {"center": tuple(center), "radii": tuple(radii), "z": z}, 2)

    @staticmethod
    def polygon(points, z: float = 0.0) -> "Domain":
        if points is None or len(points) < 3:
            raise ValueError("polygon requires at least 3 points.")
        convex = _convex_hull_2d(points)
        if len(convex) < 3:
            raise ValueError("polygon is degenerate.")
        if _polygon_signed_area(convex) <= 0:
            convex = list(reversed(convex))
        return Domain("polygon", {"points": convex, "z": z}, 2)

    @staticmethod
    def box(center: Float3 = (0.0, 0.0, 0.0), size: Float3 = (10.0, 10.0, 10.0)) -> "Domain":
        _ensure_positive_tuple(size, 3, "size")
        return Domain("box", {"center": tuple(center), "size": tuple(size)}, 3)

    @staticmethod
    def cylinder(
        center: Float3 = (0.0, 0.0, 0.0),
        radius: float = 5.0,
        height: float = 10.0,
        axis: str = "Z",
    ) -> "Domain":
        if radius <= 0:
            raise ValueError("radius must be > 0.")
        if height <= 0:
            raise ValueError("height must be > 0.")
        axis_up = axis.upper()
        if axis_up not in {"X", "Y", "Z"}:
            raise ValueError("axis must be one of: X, Y, Z.")
        return Domain(
            "cylinder",
            {"center": tuple(center), "radius": radius, "height": height, "axis": axis_up},
            3,
        )

    @staticmethod
    def ellipsoid(
        center: Float3 = (0.0, 0.0, 0.0),
        radii: Float3 = (5.0, 3.0, 2.0),
    ) -> "Domain":
        _ensure_positive_tuple(radii, 3, "radii")
        return Domain("ellipsoid", {"center": tuple(center), "radii": tuple(radii)}, 3)

    @staticmethod
    def convex_hull(rv_obj: "Object", project_2d: bool = False) -> "Domain":
        points = _get_object_world_vertices(rv_obj.obj)
        if len(points) < 3:
            raise ValueError("convex_hull requires an object with mesh geometry.")
        if project_2d:
            hull = _convex_hull_2d([(p.x, p.y) for p in points])
            if len(hull) < 3:
                raise ValueError("2D projected convex hull is degenerate.")
            if _polygon_signed_area(hull) <= 0:
                hull = list(reversed(hull))
            z = float(rv_obj.obj.location.z)
            return Domain("hull2d", {"points": hull, "z": z}, 2)

        planes = _convex_hull_planes(points)
        if len(planes) < 4:
            raise ValueError("3D convex hull is degenerate.")
        aabb_min, aabb_max = _aabb_from_points(points)
        return Domain(
            "hull3d",
            {
                "planes": planes,
                "aabb_min": tuple(aabb_min),
                "aabb_max": tuple(aabb_max),
                "centroid": tuple(_points_centroid(points)),
            },
            3,
        )

    def sample_point(self, rng: random.Random) -> mathutils.Vector:
        inset_margin = self._effective_inset_margin()
        if self.kind == "rect":
            cx, cy = self.data["center"]
            sx, sy = self.data["size"]
            half_x = sx * 0.5 - inset_margin
            half_y = sy * 0.5 - inset_margin
            if half_x <= 0 or half_y <= 0:
                raise ValueError("domain inset is too large to sample from rect.")
            z = self.data["z"]
            return Vector((rng.uniform(cx - half_x, cx + half_x), rng.uniform(cy - half_y, cy + half_y), z))
        if self.kind == "ellipse":
            cx, cy = self.data["center"]
            rx, ry = self.data["radii"]
            rx_in = rx - inset_margin
            ry_in = ry - inset_margin
            if rx_in <= 0 or ry_in <= 0:
                raise ValueError("domain inset is too large to sample from ellipse.")
            z = self.data["z"]
            theta = rng.uniform(0.0, 2.0 * math.pi)
            rr = math.sqrt(rng.random())
            return Vector((cx + rr * rx_in * math.cos(theta), cy + rr * ry_in * math.sin(theta), z))
        if self.kind in {"polygon", "hull2d"}:
            points = self.data["points"]
            z = self.data["z"]
            for _ in range(512):
                x, y = _sample_convex_polygon(points, rng)
                p = Vector((x, y, z))
                if self.contains_point(p, margin=0.0):
                    return p
            raise ValueError("domain inset is too large to sample from polygon/hull2d.")
        if self.kind == "box":
            cx, cy, cz = self.data["center"]
            sx, sy, sz = self.data["size"]
            hx = sx * 0.5 - inset_margin
            hy = sy * 0.5 - inset_margin
            hz = sz * 0.5 - inset_margin
            if hx <= 0 or hy <= 0 or hz <= 0:
                raise ValueError("domain inset is too large to sample from box.")
            return Vector((rng.uniform(cx - hx, cx + hx), rng.uniform(cy - hy, cy + hy), rng.uniform(cz - hz, cz + hz)))
        if self.kind == "cylinder":
            cx, cy, cz = self.data["center"]
            radius = self.data["radius"] - inset_margin
            half_h = self.data["height"] * 0.5 - inset_margin
            if radius <= 0 or half_h <= 0:
                raise ValueError("domain inset is too large to sample from cylinder.")
            axis = self.data["axis"]
            theta = rng.uniform(0.0, 2.0 * math.pi)
            rr = math.sqrt(rng.random()) * radius
            h = rng.uniform(-half_h, half_h)
            if axis == "X":
                return Vector((cx + h, cy + rr * math.cos(theta), cz + rr * math.sin(theta)))
            if axis == "Y":
                return Vector((cx + rr * math.cos(theta), cy + h, cz + rr * math.sin(theta)))
            return Vector((cx + rr * math.cos(theta), cy + rr * math.sin(theta), cz + h))
        if self.kind == "ellipsoid":
            cx, cy, cz = self.data["center"]
            rx, ry, rz = self.data["radii"]
            rx_in = rx - inset_margin
            ry_in = ry - inset_margin
            rz_in = rz - inset_margin
            if rx_in <= 0 or ry_in <= 0 or rz_in <= 0:
                raise ValueError("domain inset is too large to sample from ellipsoid.")
            direction = _random_unit_vector(rng)
            radial = rng.random() ** (1.0 / 3.0)
            return Vector((cx + direction.x * rx_in * radial, cy + direction.y * ry_in * radial, cz + direction.z * rz_in * radial))
        if self.kind == "hull3d":
            aabb_min = Vector(self.data["aabb_min"])
            aabb_max = Vector(self.data["aabb_max"])
            for _ in range(512):
                p = Vector((rng.uniform(aabb_min.x, aabb_max.x), rng.uniform(aabb_min.y, aabb_max.y), rng.uniform(aabb_min.z, aabb_max.z)))
                if self.contains_point(p, margin=0.0):
                    return p
            return Vector(self.data["centroid"])
        raise ValueError(f"Unsupported domain kind: {self.kind}")

    def contains_point(self, point: mathutils.Vector, margin: float = 0.0) -> bool:
        if margin < 0:
            raise ValueError("margin must be >= 0.")
        margin = float(margin) + float(self.data.get("inset_margin", 0.0))
        if self.kind == "rect":
            cx, cy = self.data["center"]
            sx, sy = self.data["size"]
            half_x = sx * 0.5 - margin
            half_y = sy * 0.5 - margin
            if half_x <= 0 or half_y <= 0:
                return False
            return abs(point.x - cx) <= half_x + 1e-9 and abs(point.y - cy) <= half_y + 1e-9 and abs(point.z - self.data["z"]) <= 1e-6
        if self.kind == "ellipse":
            cx, cy = self.data["center"]
            rx, ry = self.data["radii"]
            rx_in = rx - margin
            ry_in = ry - margin
            if rx_in <= 0 or ry_in <= 0:
                return False
            dx = (point.x - cx) / rx_in
            dy = (point.y - cy) / ry_in
            return dx * dx + dy * dy <= 1.0 + 1e-9 and abs(point.z - self.data["z"]) <= 1e-6
        if self.kind in {"polygon", "hull2d"}:
            if abs(point.z - self.data["z"]) > 1e-6:
                return False
            pt = (point.x, point.y)
            if not _point_in_convex_polygon(pt, self.data["points"]):
                return False
            if margin <= 0:
                return True
            return _distance_to_polygon_edges(pt, self.data["points"]) >= margin - 1e-9
        if self.kind == "box":
            cx, cy, cz = self.data["center"]
            sx, sy, sz = self.data["size"]
            hx = sx * 0.5 - margin
            hy = sy * 0.5 - margin
            hz = sz * 0.5 - margin
            if hx <= 0 or hy <= 0 or hz <= 0:
                return False
            return abs(point.x - cx) <= hx + 1e-9 and abs(point.y - cy) <= hy + 1e-9 and abs(point.z - cz) <= hz + 1e-9
        if self.kind == "cylinder":
            cx, cy, cz = self.data["center"]
            radius = self.data["radius"] - margin
            half_h = self.data["height"] * 0.5 - margin
            if radius <= 0 or half_h <= 0:
                return False
            axis = self.data["axis"]
            if axis == "X":
                radial = math.hypot(point.y - cy, point.z - cz)
                return radial <= radius + 1e-9 and abs(point.x - cx) <= half_h + 1e-9
            if axis == "Y":
                radial = math.hypot(point.x - cx, point.z - cz)
                return radial <= radius + 1e-9 and abs(point.y - cy) <= half_h + 1e-9
            radial = math.hypot(point.x - cx, point.y - cy)
            return radial <= radius + 1e-9 and abs(point.z - cz) <= half_h + 1e-9
        if self.kind == "ellipsoid":
            cx, cy, cz = self.data["center"]
            rx, ry, rz = self.data["radii"]
            rx_in = rx - margin
            ry_in = ry - margin
            rz_in = rz - margin
            if rx_in <= 0 or ry_in <= 0 or rz_in <= 0:
                return False
            dx = (point.x - cx) / rx_in
            dy = (point.y - cy) / ry_in
            dz = (point.z - cz) / rz_in
            return dx * dx + dy * dy + dz * dz <= 1.0 + 1e-9
        if self.kind == "hull3d":
            for nx, ny, nz, d in self.data["planes"]:
                if nx * point.x + ny * point.y + nz * point.z + d > -margin + 1e-9:
                    return False
            return True
        raise ValueError(f"Unsupported domain kind: {self.kind}")

    def contains_object(self, obj: "Object", margin: float = 0.0, mode: Literal["aabb", "mesh"] = "mesh") -> bool:
        if not isinstance(obj, Object):
            raise TypeError("obj must be an instance of Object.")
        if margin < 0:
            raise ValueError("margin must be >= 0.")
        if mode not in {"aabb", "mesh"}:
            raise ValueError("mode must be one of: aabb, mesh.")
        if mode == "aabb":
            bounds = obj.get_bounds(space="world")
            pmin = Vector(bounds["min"])
            pmax = Vector(bounds["max"])
            corners = [Vector((x, y, z)) for x in (pmin.x, pmax.x) for y in (pmin.y, pmax.y) for z in (pmin.z, pmax.z)]
            return all(self.contains_point(corner, margin=margin) for corner in corners)
        points = _get_object_world_vertices(obj.obj)
        if len(points) == 0:
            bounds = obj.get_bounds(space="world")
            pmin = Vector(bounds["min"])
            pmax = Vector(bounds["max"])
            points = [Vector((x, y, z)) for x in (pmin.x, pmax.x) for y in (pmin.y, pmax.y) for z in (pmin.z, pmax.z)]
        return all(self.contains_point(point, margin=margin) for point in points)

    def aabb(self) -> AABB:
        inset_margin = self._effective_inset_margin()
        if self.kind == "rect":
            cx, cy = self.data["center"]
            sx, sy = self.data["size"]
            half_x = max(0.0, sx * 0.5 - inset_margin)
            half_y = max(0.0, sy * 0.5 - inset_margin)
            z = self.data["z"]
            return Vector((cx - half_x, cy - half_y, z)), Vector((cx + half_x, cy + half_y, z))
        if self.kind == "ellipse":
            cx, cy = self.data["center"]
            rx, ry = self.data["radii"]
            rx_in = max(0.0, rx - inset_margin)
            ry_in = max(0.0, ry - inset_margin)
            z = self.data["z"]
            return Vector((cx - rx_in, cy - ry_in, z)), Vector((cx + rx_in, cy + ry_in, z))
        if self.kind in {"polygon", "hull2d"}:
            xs = [p[0] for p in self.data["points"]]
            ys = [p[1] for p in self.data["points"]]
            z = self.data["z"]
            return Vector((min(xs), min(ys), z)), Vector((max(xs), max(ys), z))
        if self.kind == "box":
            cx, cy, cz = self.data["center"]
            sx, sy, sz = self.data["size"]
            hx = max(0.0, sx * 0.5 - inset_margin)
            hy = max(0.0, sy * 0.5 - inset_margin)
            hz = max(0.0, sz * 0.5 - inset_margin)
            return Vector((cx - hx, cy - hy, cz - hz)), Vector((cx + hx, cy + hy, cz + hz))
        if self.kind == "cylinder":
            cx, cy, cz = self.data["center"]
            r = max(0.0, self.data["radius"] - inset_margin)
            h = max(0.0, self.data["height"] * 0.5 - inset_margin)
            axis = self.data["axis"]
            if axis == "X":
                return Vector((cx - h, cy - r, cz - r)), Vector((cx + h, cy + r, cz + r))
            if axis == "Y":
                return Vector((cx - r, cy - h, cz - r)), Vector((cx + r, cy + h, cz + r))
            return Vector((cx - r, cy - r, cz - h)), Vector((cx + r, cy + r, cz + h))
        if self.kind == "ellipsoid":
            cx, cy, cz = self.data["center"]
            rx, ry, rz = self.data["radii"]
            rx_in = max(0.0, rx - inset_margin)
            ry_in = max(0.0, ry - inset_margin)
            rz_in = max(0.0, rz - inset_margin)
            return Vector((cx - rx_in, cy - ry_in, cz - rz_in)), Vector((cx + rx_in, cy + ry_in, cz + rz_in))
        if self.kind == "hull3d":
            return Vector(self.data["aabb_min"]), Vector(self.data["aabb_max"])
        raise ValueError(f"Unsupported domain kind: {self.kind}")


class _SpatialHash:
    def __init__(self, cell_size: float, dimension: int) -> None:
        self.cell_size = max(cell_size, 1e-6)
        self.dimension = dimension
        self.cells: dict[CellCoords, list[int]] = {}

    def _cell_coords(self, point: mathutils.Vector) -> CellCoords:
        if self.dimension == 2:
            return (math.floor(point.x / self.cell_size), math.floor(point.y / self.cell_size))
        return (
            math.floor(point.x / self.cell_size),
            math.floor(point.y / self.cell_size),
            math.floor(point.z / self.cell_size),
        )

    def insert(self, point: mathutils.Vector, idx: int) -> None:
        cell = self._cell_coords(point)
        if cell not in self.cells:
            self.cells[cell] = []
        self.cells[cell].append(idx)

    def neighbors(self, point: mathutils.Vector) -> list[int]:
        base = self._cell_coords(point)
        result: list[int] = []
        if self.dimension == 2:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    result.extend(self.cells.get((base[0] + dx, base[1] + dy), []))
            return result
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    result.extend(self.cells.get((base[0] + dx, base[1] + dy, base[2] + dz), []))
        return result


class Scene(ABC, _Serializable):
    resolution: Resolution = (640, 640)
    time_limit: float = 3.0
    passes: RenderPassSet = None
    output_dir: Optional[str]
    subdir: str
    camera: "Camera"
    world: "World"
    tags: TagSet
    objects: set["Object"]
    materials: set["Material"]
    lights: set["Light"]
    semantic_channels: SemanticChannelSet
    semantic_mask_threshold: float = 0.5
    object_index_counter: int = 0
    material_index_counter: int = 0
    light_index_counter: int = 0

    @abstractmethod
    def generate(self) -> None:
        pass

    def __init__(self, output_dir=None) -> None:
        super().__init__()
        self.passes = set()
        self.output_dir = output_dir
        self.subdir = None
        self.objects = set()
        self.materials = set()
        self.lights = set()
        self.tags = set()
        self.semantic_channels = set()
        self.semantic_mask_threshold = 0.5
        self.object_index_counter = 0
        self.material_index_counter = 0
        self.light_index_counter = 0

        _get_generated_collection()
        bpy.ops.object.camera_add()
        _move_object_to_generated_collection(bpy.context.active_object)
        _mark_object_tree(bpy.context.active_object)
        self.camera = Camera(bpy.context.active_object, self)
        bpy.context.scene.camera = self.camera.obj
        self.camera.set_location(mathutils.Vector((0, 0, 10)))
        self._set_user_view()
        from .world import SkyWorld

        self.world = SkyWorld()

    def set_rendering_time_limit(self, time_limit: float = 3.0):
        self.time_limit = time_limit
        return self

    def set_passes(self, *passes: tuple[RenderPass | list[RenderPass], ...]):
        self.passes = _combine_arglist_set(passes)
        return self

    def enable_semantic_channels(self, *channels: tuple[str | list[str], ...]) -> "Scene":
        for channel in _combine_arglist_set(channels):
            self.semantic_channels.add(_normalize_semantic_channel(channel))
        return self

    def set_semantic_mask_threshold(self, threshold: float) -> "Scene":
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("semantic mask threshold must be in [0, 1].")
        self.semantic_mask_threshold = threshold
        return self

    def create_empty(self, name: str = "Empty") -> "Object":
        empty = bpy.data.objects.new(name, None)
        _mark_object_tree(empty)
        _get_generated_collection().objects.link(empty)
        return Object(empty, self)

    def create_sphere(self, name: str = "Sphere", radius: float = 1.0, segments: int = 32, ring_count: int = 16) -> "Object":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments, ring_count=ring_count)
        sphere = bpy.context.active_object
        _move_object_to_generated_collection(sphere)
        _mark_object_tree(sphere)
        sphere.name = name
        return Object(sphere, self)

    def create_cube(self, name: str = "Cube", size: float = 2.0) -> "Object":
        bpy.ops.mesh.primitive_cube_add(size=size)
        cube = bpy.context.active_object
        _move_object_to_generated_collection(cube)
        _mark_object_tree(cube)
        cube.name = name
        return Object(cube, self)

    def create_plane(self, name: str = "Plane", size: float = 2.0) -> "Object":
        bpy.ops.mesh.primitive_plane_add(size=size)
        plane = bpy.context.active_object
        _move_object_to_generated_collection(plane)
        _mark_object_tree(plane)
        plane.name = name
        return Object(plane, self)

    def create_point_light(self, name: str = "Point", power: float = 1000.0) -> "PointLight":
        light_data = bpy.data.lights.new(name=name, type="POINT")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return PointLight(light_obj, self).set_power(power)

    def create_sun_light(self, name: str = "Sun", power: float = 1.0) -> "SunLight":
        light_data = bpy.data.lights.new(name=name, type="SUN")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return SunLight(light_obj, self).set_power(power)

    def create_area_light(self, name: str = "Area", power: float = 100.0) -> "AreaLight":
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return AreaLight(light_obj, self).set_power(power)

    def create_spot_light(self, name: str = "Spot", power: float = 1000.0) -> "SpotLight":
        light_data = bpy.data.lights.new(name=name, type="SPOT")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return SpotLight(light_obj, self).set_power(power)

    def get_camera(self) -> "Camera":
        return self.camera

    def set_world(self, world: "World") -> "World":
        self.world = world
        return world

    def get_world(self) -> "World":
        return self.world

    def set_tags(self, *tags) -> "Scene":
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(self, *tags) -> "Scene":
        self.tags |= _combine_arglist_set(tags)
        return self

    def load_object(self, blendfile: str, import_name: str = None) -> "ObjectLoader":
        path = str(pathlib.Path(blendfile).expanduser())
        if import_name is None:
            obj = _load_single_object(path)
            _mark_object_tree(obj)
            return ObjectLoader(obj, self)
        objects = _load_all_objects(path)
        for obj in objects:
            _mark_object_tree(obj)
            if obj.name == import_name:
                return ObjectLoader(obj, self)
        object_names = ", ".join(obj.name for obj in objects)
        raise ValueError(
            f"Object '{import_name}' was not found in '{path}'. "
            f"Available objects: [{object_names}]"
        )

    def load_objects(self, blendfile: str, import_names: list[str] = None) -> list["ObjectLoader"]:
        path = str(pathlib.Path(blendfile).expanduser())
        objects = _load_all_objects(path)
        res = []
        if import_names is None:
            for obj in objects:
                _mark_object_tree(obj)
                res.append(ObjectLoader(obj, self))
        else:
            import_names_set = set(import_names)
            found_import_names = set()
            for obj in objects:
                _mark_object_tree(obj)
                if obj.name in import_names_set:
                    found_import_names.add(obj.name)
                    res.append(ObjectLoader(obj, self))
            missing = import_names_set - found_import_names
            if missing:
                missing_sorted = ", ".join(sorted(missing))
                available = ", ".join(obj.name for obj in objects)
                raise ValueError(
                    f"Objects [{missing_sorted}] were not found in '{path}'. "
                    f"Available objects: [{available}]"
                )
        return res

    def create_material(self, name: str = "Material") -> "BasicMaterial":
        return BasicMaterial(name=name)

    def import_material(self, blendfile: str, material_name: str = None) -> "ImportedMaterial":
        path = str(pathlib.Path(blendfile).expanduser())
        return ImportedMaterial(filepath=path, material_name=material_name)

    def inspect_object(self, loader_or_obj: Union["ObjectLoader", "Object"], applied_scale: bool = True) -> ObjectStats:
        temp_obj = None
        if isinstance(loader_or_obj, ObjectLoader):
            temp_obj = loader_or_obj.create_instance(register_object=False)
            obj = temp_obj
        elif isinstance(loader_or_obj, Object):
            obj = loader_or_obj
        else:
            raise TypeError("loader_or_obj must be ObjectLoader or Object.")
        try:
            dims_world = obj.get_dimensions(space="world")
            dims_local = obj.get_dimensions(space="local")
            if applied_scale:
                dims_local_out = (
                    dims_local[0] * float(obj.obj.scale.x),
                    dims_local[1] * float(obj.obj.scale.y),
                    dims_local[2] * float(obj.obj.scale.z),
                )
            else:
                dims_local_out = dims_local
            stats = ObjectStats(
                name=str(obj.obj.name),
                type=str(obj.obj.type),
                dimensions_world=dims_world,
                dimensions_local=dims_local_out,
                bounds_world=obj.get_bounds(space="world"),
                bounds_local=obj.get_bounds(space="local"),
                scale=tuple(float(v) for v in obj.obj.scale),
            )
            inspected = self.custom_meta.get("inspected_objects", [])
            if not isinstance(inspected, list):
                inspected = [inspected]
            inspected.append(stats.to_dict())
            self.custom_meta["inspected_objects"] = inspected
            return stats
        finally:
            if temp_obj is not None:
                _remove_blender_object(temp_obj.obj)

    def scatter_by_sphere(self, source: ObjectLoaderSource, count: int, domain: "Domain", min_gap: float = 0.0, yaw_range: Float2 = (0.0, 360.0), rotation_mode: Literal["yaw", "free"] = "yaw", scale_range: Float2 = (1.0, 1.0), max_attempts_per_object: int = 100, boundary_mode: Literal["center_margin"] = "center_margin", boundary_margin: float = 0.0, seed: int | None = None) -> list["Object"]:
        loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(source, count, domain, min_gap, yaw_range, rotation_mode, scale_range, max_attempts_per_object, boundary_mode, boundary_margin)
        rng = random.Random(seed)
        base_radii: dict[int, float] = {}
        max_scaled_radius = 0.0
        for idx, loader in enumerate(loaders):
            radius = _estimate_loader_radius(loader, domain.dimension)
            base_radii[idx] = radius
            max_scaled_radius = max(max_scaled_radius, radius * scale_max)
        cell_size = max(1e-6, (2.0 * max_scaled_radius) + min_gap)
        grid = _SpatialHash(cell_size=cell_size, dimension=domain.dimension)
        placed: list[Object] = []
        placed_infos: list[dict] = []
        stats = _init_scatter_stats(count, domain.kind, "sphere", seed)
        for _ in range(count):
            loader_idx = rng.randrange(0, len(loaders))
            loader = loaders[loader_idx]
            placed_one = False
            for _attempt in range(max_attempts_per_object):
                stats["attempts"] += 1
                scale = rng.uniform(scale_min, scale_max)
                pos = domain.sample_point(rng)
                if not domain.contains_point(pos, margin=boundary_margin):
                    stats["rejected_boundary"] += 1
                    continue
                rot = _sample_rotation_quaternion(rng=rng, domain_dimension=domain.dimension, rotation_mode=rotation_mode, yaw_min=yaw_min, yaw_max=yaw_max)
                radius = base_radii[loader_idx] * scale
                neighbors = grid.neighbors(pos)
                if _overlaps_by_radius(pos, radius, neighbors, placed_infos, domain.dimension, min_gap):
                    stats["rejected_overlap"] += 1
                    continue
                obj = loader.create_instance()
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                placed.append(obj)
                placed_infos.append({"position": Vector(pos), "radius": radius, "object": obj})
                grid.insert(pos, len(placed_infos) - 1)
                placed_one = True
                break
            if not placed_one:
                stats["rejected_attempt_limit"] += 1
        _finalize_scatter_stats(self, stats=stats, placed=placed, requested=count)
        return placed

    def scatter_by_bvh(self, source: ObjectLoaderSource, count: int, domain: "Domain", min_gap: float = 0.0, yaw_range: Float2 = (0.0, 360.0), rotation_mode: Literal["yaw", "free"] = "yaw", scale_range: Float2 = (1.0, 1.0), max_attempts_per_object: int = 100, boundary_mode: Literal["center_margin"] = "center_margin", boundary_margin: float = 0.0, seed: int | None = None) -> list["Object"]:
        loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(source, count, domain, min_gap, yaw_range, rotation_mode, scale_range, max_attempts_per_object, boundary_mode, boundary_margin)
        rng = random.Random(seed)
        base_radii: dict[int, float] = {}
        max_scaled_radius = 0.0
        for idx, loader in enumerate(loaders):
            radius = _estimate_loader_radius(loader, domain.dimension)
            base_radii[idx] = radius
            max_scaled_radius = max(max_scaled_radius, radius * scale_max)
        cell_size = max(1e-6, (2.0 * max_scaled_radius) + min_gap)
        grid = _SpatialHash(cell_size=cell_size, dimension=domain.dimension)
        placed: list[Object] = []
        placed_infos: list[dict] = []
        stats = _init_scatter_stats(count, domain.kind, "bvh", seed)
        for _ in range(count):
            loader_idx = rng.randrange(0, len(loaders))
            loader = loaders[loader_idx]
            placed_one = False
            for _attempt in range(max_attempts_per_object):
                stats["attempts"] += 1
                scale = rng.uniform(scale_min, scale_max)
                pos = domain.sample_point(rng)
                if not domain.contains_point(pos, margin=boundary_margin):
                    stats["rejected_boundary"] += 1
                    continue
                rot = _sample_rotation_quaternion(rng=rng, domain_dimension=domain.dimension, rotation_mode=rotation_mode, yaw_min=yaw_min, yaw_max=yaw_max)
                radius = base_radii[loader_idx] * scale
                neighbors = grid.neighbors(pos)
                if _overlaps_by_radius(pos, radius, neighbors, placed_infos, domain.dimension, min_gap):
                    stats["rejected_overlap"] += 1
                    continue
                temp_obj = loader.create_instance(register_object=False)
                temp_obj.set_scale(scale).set_rotation(rot).set_location(pos)
                neighbor_objs = [placed_infos[idx]["object"].obj for idx in neighbors]
                if _mesh_object_overlaps_any(temp_obj.obj, neighbor_objs):
                    _remove_blender_object(temp_obj.obj)
                    stats["rejected_overlap"] += 1
                    continue
                _remove_blender_object(temp_obj.obj)
                obj = loader.create_instance()
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                placed.append(obj)
                placed_infos.append({"position": Vector(pos), "radius": radius, "object": obj})
                grid.insert(pos, len(placed_infos) - 1)
                placed_one = True
                break
            if not placed_one:
                stats["rejected_attempt_limit"] += 1
        _finalize_scatter_stats(self, stats=stats, placed=placed, requested=count)
        return placed

    def scatter_parametric(self, source: "ParametricSource", count: int, domain: "Domain", strategy: Literal["sphere", "bvh"] = "sphere", min_gap: float = 0.0, yaw_range: Float2 = (0.0, 360.0), rotation_mode: Literal["yaw", "free"] = "yaw", scale_range: Float2 = (1.0, 1.0), max_attempts_per_object: int = 100, boundary_mode: Literal["center_margin"] = "center_margin", boundary_margin: float = 0.0, seed: int | None = None) -> list["Object"]:
        if not isinstance(source, ParametricSource):
            raise TypeError("source must be ParametricSource.")
        if strategy not in {"sphere", "bvh"}:
            raise ValueError("strategy must be one of: sphere, bvh.")
        _loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(source.source, count, domain, min_gap, yaw_range, rotation_mode, scale_range, max_attempts_per_object, boundary_mode, boundary_margin)
        rng = random.Random(seed)
        placed: list[Object] = []
        placed_infos: list[dict] = []
        stats = _init_scatter_stats(count, domain.kind, f"parametric_{strategy}", seed)
        for _ in range(count):
            placed_one = False
            for _attempt in range(max_attempts_per_object):
                stats["attempts"] += 1
                params = source.sample_params(rng)
                scale = rng.uniform(scale_min, scale_max)
                pos = domain.sample_point(rng)
                if not domain.contains_point(pos, margin=boundary_margin):
                    stats["rejected_boundary"] += 1
                    continue
                rot = _sample_rotation_quaternion(rng=rng, domain_dimension=domain.dimension, rotation_mode=rotation_mode, yaw_min=yaw_min, yaw_max=yaw_max)
                temp_obj = source.create_instance(params=params, register_object=False)
                temp_obj.set_scale(scale).set_rotation(rot).set_location(pos)
                radius = _object_world_radius(temp_obj.obj, domain.dimension)
                neighbors = list(range(len(placed_infos)))
                if _overlaps_by_radius(pos, radius, neighbors, placed_infos, domain.dimension, min_gap):
                    _remove_blender_object(temp_obj.obj)
                    stats["rejected_overlap"] += 1
                    continue
                if strategy == "bvh":
                    neighbor_objs = [placed_infos[idx]["object"].obj for idx in neighbors]
                    if _mesh_object_overlaps_any(temp_obj.obj, neighbor_objs):
                        _remove_blender_object(temp_obj.obj)
                        stats["rejected_overlap"] += 1
                        continue
                _remove_blender_object(temp_obj.obj)
                obj = source.create_instance(params=params, register_object=True)
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                placed.append(obj)
                placed_infos.append({"position": Vector(pos), "radius": radius, "object": obj, "params": params})
                placed_one = True
                break
            if not placed_one:
                stats["rejected_attempt_limit"] += 1
        _finalize_scatter_stats(self, stats=stats, placed=placed, requested=count)
        return placed

    def _set_user_view(self) -> None:
        for area in bpy.context.screen.areas:
            if area.type == "VIEW_3D":
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        space.region_3d.view_perspective = "CAMERA"
                        break

    def _post_gen(self) -> None:
        _set_resolution(self.resolution)
        _set_time_limit(self.time_limit)
        _use_gpu()
        _use_cycles()
        _deselect()
        self.world._post_gen()
        _configure_passes(self.passes, self.semantic_channels)
        if self.output_dir is None:
            _configure_compositor(None, semantic_channels=self.semantic_channels, semantic_mask_threshold=self.semantic_mask_threshold)
        else:
            if self.subdir is None:
                self.subdir = str(uuid.uuid4())
            _configure_compositor(os.path.join(self.output_dir, self.subdir), semantic_channels=self.semantic_channels, semantic_mask_threshold=self.semantic_mask_threshold)

    def _render(self) -> None:
        if self.output_dir is not None:
            bpy.ops.render.render(write_still=False)

    def _register_object(self, obj: "Object") -> int:
        self.object_index_counter += 1
        self.objects.add(obj)
        return self.object_index_counter

    def _register_material(self, material: "Material") -> int:
        self.material_index_counter += 1
        self.materials.add(material)
        return self.material_index_counter

    def _register_light(self, light: "Light") -> int:
        self.light_index_counter += 1
        self.lights.add(light)
        return self.light_index_counter

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "resolution": self.resolution,
                "time_limit": self.time_limit,
                "passes": [p.value for p in self.passes],
                "tags": list(self.tags),
                "semantic_channels": sorted(self.semantic_channels),
                "semantic_mask_threshold": self.semantic_mask_threshold,
                "objects": list(obj._get_meta() for obj in self.objects),
                "materials": list(material._get_meta() for material in self.materials),
                "lights": list(light._get_meta() for light in self.lights),
            }
        )
        return res

    def _save_metadata(self, filename: str) -> None:
        with open(os.path.join(self.output_dir, self.subdir, filename), "w") as fout:
            json.dump(self._get_meta(), fout, indent=4)
