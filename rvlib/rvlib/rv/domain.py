import math
import random
import warnings
from mathutils import Vector
from typing import Literal, Protocol

import mathutils

from .geometry import (
    _aabb_from_points,
    _convex_hull_2d,
    _convex_hull_planes,
    _distance_to_polygon_edges,
    _get_object_world_vertices,
    _is_convex_polygon,
    _point_in_polygon,
    _points_centroid,
    _prepare_polygon_2d,
    _random_unit_vector,
    _sample_polygon,
)
from .object import Object
from .scatter import _ensure_positive_tuple
from .types import AABB, Float2, Float3


class _DomainShape(Protocol):
    kind: str
    dimension: int
    data: dict

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector: ...

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool: ...

    def aabb(self, inset_margin: float) -> AABB: ...


class _RectShape:
    kind = "rect"
    dimension = 2

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
        cx, cy = self.data["center"]
        sx, sy = self.data["size"]
        half_x = sx * 0.5 - inset_margin
        half_y = sy * 0.5 - inset_margin
        if half_x <= 0 or half_y <= 0:
            raise ValueError("domain inset is too large to sample from rect.")
        z = self.data["z"]
        return Vector(
            (rng.uniform(cx - half_x, cx + half_x), rng.uniform(cy - half_y, cy + half_y), z)
        )

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
        cx, cy = self.data["center"]
        sx, sy = self.data["size"]
        half_x = sx * 0.5 - margin
        half_y = sy * 0.5 - margin
        if half_x <= 0 or half_y <= 0:
            return False
        return (
            abs(point.x - cx) <= half_x + 1e-9
            and abs(point.y - cy) <= half_y + 1e-9
            and abs(point.z - self.data["z"]) <= 1e-6
        )

    def aabb(self, inset_margin: float) -> AABB:
        cx, cy = self.data["center"]
        sx, sy = self.data["size"]
        half_x = max(0.0, sx * 0.5 - inset_margin)
        half_y = max(0.0, sy * 0.5 - inset_margin)
        z = self.data["z"]
        return Vector((cx - half_x, cy - half_y, z)), Vector((cx + half_x, cy + half_y, z))


class _EllipseShape:
    kind = "ellipse"
    dimension = 2

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
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

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
        cx, cy = self.data["center"]
        rx, ry = self.data["radii"]
        rx_in = rx - margin
        ry_in = ry - margin
        if rx_in <= 0 or ry_in <= 0:
            return False
        dx = (point.x - cx) / rx_in
        dy = (point.y - cy) / ry_in
        return dx * dx + dy * dy <= 1.0 + 1e-9 and abs(point.z - self.data["z"]) <= 1e-6

    def aabb(self, inset_margin: float) -> AABB:
        cx, cy = self.data["center"]
        rx, ry = self.data["radii"]
        rx_in = max(0.0, rx - inset_margin)
        ry_in = max(0.0, ry - inset_margin)
        z = self.data["z"]
        return Vector((cx - rx_in, cy - ry_in, z)), Vector((cx + rx_in, cy + ry_in, z))


class _PolygonShape:
    kind = "polygon"
    dimension = 2

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
        z = self.data["z"]
        for _ in range(512):
            x, y = _sample_polygon(self.data["triangles"], rng)
            point = Vector((x, y, z))
            if self.contains_point(point, inset_margin):
                return point
        raise ValueError("domain inset is too large to sample from polygon/hull2d.")

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
        if abs(point.z - self.data["z"]) > 1e-6:
            return False
        pt = (point.x, point.y)
        if not _point_in_polygon(pt, self.data["points"]):
            return False
        if margin <= 0:
            return True
        return _distance_to_polygon_edges(pt, self.data["points"]) >= margin - 1e-9

    def aabb(self, inset_margin: float) -> AABB:
        del inset_margin
        xs = [p[0] for p in self.data["points"]]
        ys = [p[1] for p in self.data["points"]]
        z = self.data["z"]
        return Vector((min(xs), min(ys), z)), Vector((max(xs), max(ys), z))


class _Hull2DShape(_PolygonShape):
    kind = "hull2d"


class _BoxShape:
    kind = "box"
    dimension = 3

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
        cx, cy, cz = self.data["center"]
        sx, sy, sz = self.data["size"]
        hx = sx * 0.5 - inset_margin
        hy = sy * 0.5 - inset_margin
        hz = sz * 0.5 - inset_margin
        if hx <= 0 or hy <= 0 or hz <= 0:
            raise ValueError("domain inset is too large to sample from box.")
        return Vector(
            (
                rng.uniform(cx - hx, cx + hx),
                rng.uniform(cy - hy, cy + hy),
                rng.uniform(cz - hz, cz + hz),
            )
        )

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
        cx, cy, cz = self.data["center"]
        sx, sy, sz = self.data["size"]
        hx = sx * 0.5 - margin
        hy = sy * 0.5 - margin
        hz = sz * 0.5 - margin
        if hx <= 0 or hy <= 0 or hz <= 0:
            return False
        return (
            abs(point.x - cx) <= hx + 1e-9
            and abs(point.y - cy) <= hy + 1e-9
            and abs(point.z - cz) <= hz + 1e-9
        )

    def aabb(self, inset_margin: float) -> AABB:
        cx, cy, cz = self.data["center"]
        sx, sy, sz = self.data["size"]
        hx = max(0.0, sx * 0.5 - inset_margin)
        hy = max(0.0, sy * 0.5 - inset_margin)
        hz = max(0.0, sz * 0.5 - inset_margin)
        return Vector((cx - hx, cy - hy, cz - hz)), Vector((cx + hx, cy + hy, cz + hz))


class _CylinderShape:
    kind = "cylinder"
    dimension = 3

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
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

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
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

    def aabb(self, inset_margin: float) -> AABB:
        cx, cy, cz = self.data["center"]
        radius = max(0.0, self.data["radius"] - inset_margin)
        half_h = max(0.0, self.data["height"] * 0.5 - inset_margin)
        axis = self.data["axis"]
        if axis == "X":
            return Vector((cx - half_h, cy - radius, cz - radius)), Vector(
                (cx + half_h, cy + radius, cz + radius)
            )
        if axis == "Y":
            return Vector((cx - radius, cy - half_h, cz - radius)), Vector(
                (cx + radius, cy + half_h, cz + radius)
            )
        return Vector((cx - radius, cy - radius, cz - half_h)), Vector(
            (cx + radius, cy + radius, cz + half_h)
        )


class _EllipsoidShape:
    kind = "ellipsoid"
    dimension = 3

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
        cx, cy, cz = self.data["center"]
        rx, ry, rz = self.data["radii"]
        rx_in = rx - inset_margin
        ry_in = ry - inset_margin
        rz_in = rz - inset_margin
        if rx_in <= 0 or ry_in <= 0 or rz_in <= 0:
            raise ValueError("domain inset is too large to sample from ellipsoid.")
        direction = _random_unit_vector(rng)
        radial = rng.random() ** (1.0 / 3.0)
        return Vector(
            (
                cx + direction.x * rx_in * radial,
                cy + direction.y * ry_in * radial,
                cz + direction.z * rz_in * radial,
            )
        )

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
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

    def aabb(self, inset_margin: float) -> AABB:
        cx, cy, cz = self.data["center"]
        rx, ry, rz = self.data["radii"]
        rx_in = max(0.0, rx - inset_margin)
        ry_in = max(0.0, ry - inset_margin)
        rz_in = max(0.0, rz - inset_margin)
        return Vector((cx - rx_in, cy - ry_in, cz - rz_in)), Vector(
            (cx + rx_in, cy + ry_in, cz + rz_in)
        )


class _Hull3DShape:
    kind = "hull3d"
    dimension = 3

    def __init__(self, data: dict):
        self.data = data

    def sample_point(self, rng: random.Random, inset_margin: float) -> mathutils.Vector:
        aabb_min = Vector(self.data["aabb_min"])
        aabb_max = Vector(self.data["aabb_max"])
        for _ in range(512):
            point = Vector(
                (
                    rng.uniform(aabb_min.x, aabb_max.x),
                    rng.uniform(aabb_min.y, aabb_max.y),
                    rng.uniform(aabb_min.z, aabb_max.z),
                )
            )
            if self.contains_point(point, inset_margin):
                return point
        return Vector(self.data["centroid"])

    def contains_point(self, point: mathutils.Vector, margin: float) -> bool:
        for nx, ny, nz, d in self.data["planes"]:
            if nx * point.x + ny * point.y + nz * point.z + d > -margin + 1e-9:
                return False
        return True

    def aabb(self, inset_margin: float) -> AABB:
        del inset_margin
        return Vector(self.data["aabb_min"]), Vector(self.data["aabb_max"])


_SHAPE_TYPES = {
    "rect": _RectShape,
    "ellipse": _EllipseShape,
    "polygon": _PolygonShape,
    "hull2d": _Hull2DShape,
    "box": _BoxShape,
    "cylinder": _CylinderShape,
    "ellipsoid": _EllipsoidShape,
    "hull3d": _Hull3DShape,
}


def _build_shape(kind: str, data: dict, dimension: int) -> _DomainShape:
    try:
        shape_cls = _SHAPE_TYPES[kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported domain kind: {kind}") from exc

    shape = shape_cls(data)
    if shape.dimension != dimension:
        raise ValueError(f"Invalid dimension {dimension} for domain kind: {kind}")
    return shape


class Domain:
    """
    Scatter domain descriptor used by scene scattering methods.
    """

    def __init__(self, kind: str, data: dict, dimension: int):
        self._shape = _build_shape(kind, data, dimension)

    @property
    def kind(self) -> str:
        return self._shape.kind

    @property
    def data(self) -> dict:
        return self._shape.data

    @property
    def dimension(self) -> int:
        return self._shape.dimension

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
    def rect(
        center: Float2 = (0.0, 0.0),
        size: Float2 = (10.0, 10.0),
        z: float = 0.0,
    ) -> "Domain":
        _ensure_positive_tuple(size, 2, "size")
        return Domain("rect", {"center": tuple(center), "size": tuple(size), "z": z}, 2)

    @staticmethod
    def ellipse(
        center: Float2 = (0.0, 0.0),
        radii: Float2 = (5.0, 3.0),
        z: float = 0.0,
    ) -> "Domain":
        _ensure_positive_tuple(radii, 2, "radii")
        return Domain(
            "ellipse",
            {"center": tuple(center), "radii": tuple(radii), "z": z},
            2,
        )

    @staticmethod
    def polygon(points, z: float = 0.0) -> "Domain":
        if points is None:
            raise ValueError("polygon requires at least 3 points.")
        polygon_points, triangles = _prepare_polygon_2d(points)
        return Domain("polygon", {"points": polygon_points, "triangles": triangles, "z": z}, 2)

    @staticmethod
    def convex_polygon(points, z: float = 0.0) -> "Domain":
        polygon = Domain.polygon(points, z=z)
        if not _is_convex_polygon(polygon.data["points"]):
            raise ValueError("convex_polygon requires convex input.")
        return Domain("hull2d", dict(polygon.data), 2)

    @staticmethod
    def box(
        center: Float3 = (0.0, 0.0, 0.0),
        size: Float3 = (10.0, 10.0, 10.0),
    ) -> "Domain":
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
            {
                "center": tuple(center),
                "radius": radius,
                "height": height,
                "axis": axis_up,
            },
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
    def convex_hull_2d(rv_obj: Object) -> "Domain":
        points = _get_object_world_vertices(rv_obj.obj)
        if len(points) < 3:
            raise ValueError("convex_hull requires an object with mesh geometry.")
        hull = _convex_hull_2d([(p.x, p.y) for p in points])
        if len(hull) < 3:
            raise ValueError("2D projected convex hull is degenerate.")
        polygon_points, triangles = _prepare_polygon_2d(hull)
        z = float(rv_obj.obj.location.z)
        return Domain("hull2d", {"points": polygon_points, "triangles": triangles, "z": z}, 2)

    @staticmethod
    def convex_hull_3d(rv_obj: Object) -> "Domain":
        points = _get_object_world_vertices(rv_obj.obj)
        if len(points) < 3:
            raise ValueError("convex_hull requires an object with mesh geometry.")
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

    @staticmethod
    def convex_hull(rv_obj: Object, project_2d: bool = False) -> "Domain":
        warnings.warn(
            "Domain.convex_hull(..., project_2d=...) is deprecated; use "
            "Domain.convex_hull_2d(...) or Domain.convex_hull_3d(...).",
            DeprecationWarning,
            stacklevel=2,
        )
        if project_2d:
            return Domain.convex_hull_2d(rv_obj)
        return Domain.convex_hull_3d(rv_obj)

    def sample_point(self, rng: random.Random) -> mathutils.Vector:
        inset_margin = self._effective_inset_margin()
        return self._shape.sample_point(rng, inset_margin)

    def contains_point(self, point: mathutils.Vector, margin: float = 0.0) -> bool:
        if margin < 0:
            raise ValueError("margin must be >= 0.")
        margin = float(margin) + float(self.data.get("inset_margin", 0.0))
        return self._shape.contains_point(point, margin)

    def contains_object(
        self,
        obj: Object,
        margin: float = 0.0,
        mode: Literal["aabb", "mesh"] = "mesh",
    ) -> bool:
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
            corners = [
                Vector((x, y, z))
                for x in (pmin.x, pmax.x)
                for y in (pmin.y, pmax.y)
                for z in (pmin.z, pmax.z)
            ]
            return all(self.contains_point(corner, margin=margin) for corner in corners)
        points = _get_object_world_vertices(obj.obj)
        if len(points) == 0:
            bounds = obj.get_bounds(space="world")
            pmin = Vector(bounds["min"])
            pmax = Vector(bounds["max"])
            points = [
                Vector((x, y, z))
                for x in (pmin.x, pmax.x)
                for y in (pmin.y, pmax.y)
                for z in (pmin.z, pmax.z)
            ]
        return all(self.contains_point(point, margin=margin) for point in points)

    def aabb(self) -> AABB:
        inset_margin = self._effective_inset_margin()
        return self._shape.aabb(inset_margin)
