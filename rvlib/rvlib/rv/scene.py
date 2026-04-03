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
from .domain import Domain
from .geometry import _mesh_object_overlaps_any, _sample_rotation_quaternion
from .material import BasicMaterial, ImportedMaterial, _normalize_semantic_channel
from .object import (
    AreaLight,
    Camera,
    Object,
    ObjectLoader,
    ObjectStats,
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
    _finalize_scatter_stats,
    _init_scatter_stats,
    _normalize_scatter_method,
    _overlaps_by_radius,
    _validate_scatter_common,
)
from .types import CellCoords, Float2, RenderPassSet, Resolution, ScatterSource, SemanticChannelSet, TagSet
from .utils import (
    _get_generated_collection,
    _mark_object_tree,
    _move_object_to_generated_collection,
)

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
    seed: int | None = None
    seed_mode: str | None = None
    object_index_counter: int = 0
    material_index_counter: int = 0
    light_index_counter: int = 0

    @abstractmethod
    def generate(self, seed: int | None = None) -> None:
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
        self.seed = None
        self.seed_mode = None
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

    def scatter(
        self,
        source: ScatterSource,
        count: int,
        domain: "Domain",
        *,
        method: Literal["auto", "fast", "exact"] = "auto",
        gap: float = 0.0,
        scale: float | Float2 = 1.0,
        rotation: Literal["yaw", "free"] = "yaw",
        yaw: Float2 = (0.0, 360.0),
        margin: float = 0.0,
        seed: int | None = None,
        unique_data: bool = False,
        on_create=None,
        max_attempts_per_object: int = 100,
    ) -> list["Object"]:
        loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(
            source,
            count,
            domain,
            gap,
            yaw,
            rotation,
            scale,
            max_attempts_per_object,
            margin,
        )
        resolved_method = _normalize_scatter_method(method, domain, rotation)
        rng = random.Random(seed)
        base_radii: dict[int, float] = {}
        max_scaled_radius = 0.0
        for idx, loader in enumerate(loaders):
            radius = _estimate_loader_radius(loader, domain.dimension)
            base_radii[idx] = radius
            max_scaled_radius = max(max_scaled_radius, radius * scale_max)
        cell_size = max(1e-6, (2.0 * max_scaled_radius) + gap)
        grid = _SpatialHash(cell_size=cell_size, dimension=domain.dimension)
        placed: list[Object] = []
        placed_infos: list[dict] = []
        stats = _init_scatter_stats(count, domain.kind, resolved_method, seed)
        for _ in range(count):
            loader_idx = rng.randrange(0, len(loaders))
            loader = loaders[loader_idx]
            placed_one = False
            for _attempt in range(max_attempts_per_object):
                stats["attempts"] += 1
                scale = rng.uniform(scale_min, scale_max)
                pos = domain.sample_point(rng)
                if not domain.contains_point(pos, margin=margin):
                    stats["rejected_boundary"] += 1
                    continue
                rot = _sample_rotation_quaternion(rng=rng, domain_dimension=domain.dimension, rotation_mode=rotation, yaw_min=yaw_min, yaw_max=yaw_max)
                radius = base_radii[loader_idx] * scale
                neighbors = grid.neighbors(pos)
                if _overlaps_by_radius(pos, radius, neighbors, placed_infos, domain.dimension, gap):
                    stats["rejected_overlap"] += 1
                    continue
                if resolved_method == "exact":
                    temp_obj = loader.create_instance(register_object=False)
                    temp_obj.set_scale(scale).set_rotation(rot).set_location(pos)
                    neighbor_objs = [placed_infos[idx]["object"].obj for idx in neighbors]
                    if _mesh_object_overlaps_any(temp_obj.obj, neighbor_objs):
                        _remove_blender_object(temp_obj.obj)
                        stats["rejected_overlap"] += 1
                        continue
                    _remove_blender_object(temp_obj.obj)
                obj = loader.create_instance(linked_data=not unique_data)
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                if on_create is not None:
                    on_create(obj, rng, len(placed))
                placed.append(obj)
                placed_infos.append({"position": Vector(pos), "radius": radius, "object": obj})
                grid.insert(pos, len(placed_infos) - 1)
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

    def _internal_post_gen(self) -> None:
        _set_resolution(self.resolution)
        _set_time_limit(self.time_limit)
        _use_gpu()
        _use_cycles()
        _deselect()
        self.world._internal_post_gen()
        _configure_passes(self.passes, self.semantic_channels)
        if self.output_dir is None:
            _configure_compositor(None, semantic_channels=self.semantic_channels, semantic_mask_threshold=self.semantic_mask_threshold)
        else:
            if self.subdir is None:
                self.subdir = str(uuid.uuid4())
            _configure_compositor(os.path.join(self.output_dir, self.subdir), semantic_channels=self.semantic_channels, semantic_mask_threshold=self.semantic_mask_threshold)

    def _internal_render(self) -> None:
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
                "seed": self.seed,
                "seed_mode": self.seed_mode,
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

    def _internal_save_metadata(self, filename: str) -> None:
        with open(os.path.join(self.output_dir, self.subdir, filename), "w") as fout:
            json.dump(self._get_meta(), fout, indent=4)
