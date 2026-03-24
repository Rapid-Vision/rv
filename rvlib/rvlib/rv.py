"""
Module for describing an `rv` scenes. To create a scene implement a class derrived from `Scene`.

- To preview scene use the `rv preview <scene.py>` command.
- To render resulting dataset use the `rv render <scene.py>` command.

View https://rv.rapid-vision.ru/ for documentation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
import numbers
import typing
from mathutils import Vector
from typing import Literal, Union, Optional, TypeAlias
import bpy
import bpy_extras
import bmesh
import json
import math
import os
import pathlib
import random
import uuid
import mathutils
import warnings
from enum import Enum
from mathutils.bvhtree import BVHTree

JSONSerializable: TypeAlias = Union[
    str, int, float, bool, None, list["JSONSerializable"], dict[str, "JSONSerializable"]
]

Resolution: TypeAlias = tuple[int, int]
Float2: TypeAlias = tuple[float, float]
Float3: TypeAlias = tuple[float, float, float]
Float4: TypeAlias = tuple[float, float, float, float]
ColorRGB: TypeAlias = Float3
ColorRGBA: TypeAlias = Float4
Color: TypeAlias = ColorRGB | ColorRGBA
OptionalColor: TypeAlias = Color | None
Polygon2D: TypeAlias = list[Float2]
AABB: TypeAlias = tuple[Vector, Vector]
CellCoords: TypeAlias = tuple[int, ...]
RenderPassSet: TypeAlias = set["RenderPass"]
TagSet: TypeAlias = set[str]
SemanticChannelSet: TypeAlias = set[str]
ObjectLoaderSource: TypeAlias = Union[
    "ObjectLoader", list["ObjectLoader"], tuple["ObjectLoader", ...]
]
ScatterValidationResult: TypeAlias = tuple[
    list["ObjectLoader"], float, float, float, float
]


@dataclass(frozen=True, slots=True)
class ObjectStats:
    """
    Geometric inspection snapshot for an object or loader instance.
    """

    name: str
    type: str
    dimensions_world: Float3
    dimensions_local: Float3
    bounds_world: dict[str, Float3]
    bounds_local: dict[str, Float3]
    scale: Float3

    def to_dict(self) -> dict[str, JSONSerializable]:
        """
        Convert to JSON-compatible dictionary for metadata serialization.
        """
        return {
            "name": self.name,
            "type": self.type,
            "dimensions_world": self.dimensions_world,
            "dimensions_local": self.dimensions_local,
            "bounds_world": self.bounds_world,
            "bounds_local": self.bounds_local,
            "scale": self.scale,
        }


class RenderPass(Enum):
    """
    Enum representing the supported render passes available for export. To enable them, use `Scene.set_passes` method.

    For full documentation view [blender docs](https://docs.blender.org/manual/en/latest/render/layers/passes.html)
    """

    # Core buffers
    Z = "Z"  # Distance to the nearest visible surface.
    VECTOR = "Vector"  # Motion vector
    MIST = "Mist"  # Distance to the nearest visible surface, mapped to the 0.0 - 1.0 range.
    POSITION = "Position"  # Positions in world space.
    NORMAL = "Normal"  # Surface normals in world space.
    UV = "UV"  # The UV coordinates within each object’s active UV map, represented through the red and green channels of the image.
    OBJECT_INDEX = "ObjectIndex"  # A map where each pixel stores the user-defined ID of the object at that pixel. It is saved as 16-bit BW image.
    MATERIAL_INDEX = "MaterialIndex"  # A map where each pixel stores the user-defined ID of the material at that pixel. It is saved as 16-bit BW image.
    SHADOW = "Shadow"  # Shadow map

    # Lighting / surface components
    AO = "AO"  # Ambient Occlusion contribution from indirect lighting.
    EMISSION = "Emission"  # Emission from materials, without influence from lighting.
    ENVIRONMENT = "Environment"  # Captures the background/environment lighting.
    SHADOW_CATCHER = "ShadowCatcher"  # Captures shadows cast on shadow catcher objects.

    # Diffuse components
    DIFFUSE_COLOR = "DiffuseColor"  # Base diffuse color of surfaces.
    DIFFUSE_DIRECT = "DiffuseDirect"  # Direct light contribution to diffuse surfaces.
    DIFFUSE_INDIRECT = (
        "DiffuseIndirect"  # Indirect light contribution to diffuse surfaces.
    )

    # Glossy components
    GLOSSY_COLOR = "GlossyColor"  # Base glossy (specular) color of surfaces.
    GLOSSY_DIRECT = "GlossyDirect"  # Direct light contribution to glossy reflections.
    GLOSSY_INDIRECT = (
        "GlossyIndirect"  # Indirect light contribution to glossy reflections.
    )

    # Transmission components
    TRANSMISSION_COLOR = "TransmissionColor"  # Base transmission color of materials.
    TRANSMISSION_DIRECT = (
        "TransmissionDirect"  # Direct light through transmissive materials.
    )
    TRANSMISSION_INDIRECT = (
        "TransmissionIndirect"  # Indirect light through transmissive materials.
    )

    # Cryptomatte passes
    CRYPTO_OBJECT = "CryptoObject"
    CRYPTO_MATERIAL = "CryptoMaterial"
    CRYPTO_ASSET = "CryptoAsset"


PASS_MAP = {
    RenderPass.Z: "use_pass_z",
    RenderPass.VECTOR: "use_pass_vector",
    RenderPass.MIST: "use_pass_mist",
    RenderPass.POSITION: "use_pass_position",
    RenderPass.NORMAL: "use_pass_normal",
    RenderPass.UV: "use_pass_uv",
    RenderPass.OBJECT_INDEX: "use_pass_object_index",
    RenderPass.MATERIAL_INDEX: "use_pass_material_index",
    RenderPass.SHADOW: "use_pass_shadow",
    RenderPass.AO: "use_pass_ambient_occlusion",
    RenderPass.EMISSION: "use_pass_emit",
    RenderPass.ENVIRONMENT: "use_pass_environment",
    RenderPass.SHADOW_CATCHER: "use_pass_shadow_catcher",
    RenderPass.DIFFUSE_COLOR: "use_pass_diffuse_color",
    RenderPass.DIFFUSE_DIRECT: "use_pass_diffuse_direct",
    RenderPass.DIFFUSE_INDIRECT: "use_pass_diffuse_indirect",
    RenderPass.GLOSSY_COLOR: "use_pass_glossy_color",
    RenderPass.GLOSSY_DIRECT: "use_pass_glossy_direct",
    RenderPass.GLOSSY_INDIRECT: "use_pass_glossy_indirect",
    RenderPass.TRANSMISSION_COLOR: "use_pass_transmission_color",
    RenderPass.TRANSMISSION_DIRECT: "use_pass_transmission_direct",
    RenderPass.TRANSMISSION_INDIRECT: "use_pass_transmission_indirect",
    RenderPass.CRYPTO_OBJECT: "use_pass_cryptomatte_object",
    RenderPass.CRYPTO_MATERIAL: "use_pass_cryptomatte_material",
    RenderPass.CRYPTO_ASSET: "use_pass_cryptomatte_asset",
}  # Map pass names to corresponding internal blender attribute names

_RV_OWNED_KEY = "_rv_owned"
_RV_RUN_ID_KEY = "_rv_run_id"
_ACTIVE_RUN_ID = None


def _mark_owned(obj: bpy.types.ID) -> None:
    if obj is None:
        return
    _ensure_active_run()
    obj[_RV_OWNED_KEY] = True
    obj[_RV_RUN_ID_KEY] = _ACTIVE_RUN_ID


def _is_owned(obj: bpy.types.ID) -> bool:
    if obj is None:
        return False
    if obj.get(_RV_OWNED_KEY, False):
        return True
    return bool(obj.get(_RV_RUN_ID_KEY))


def _ensure_active_run() -> None:
    global _ACTIVE_RUN_ID
    if _ACTIVE_RUN_ID is None:
        _ACTIVE_RUN_ID = uuid.uuid4().hex


def _mark_material_tree(material, visited: set[int] | None = None) -> None:
    if material is None:
        return
    _mark_owned(material)
    node_tree = getattr(material, "node_tree", None)
    if node_tree is not None:
        _mark_node_tree(node_tree, visited)


def _mark_node_tree(node_tree, visited: set[int] | None = None) -> None:
    if node_tree is None:
        return
    if visited is None:
        visited = set()
    ptr = node_tree.as_pointer()
    if ptr in visited:
        return
    visited.add(ptr)

    _mark_owned(node_tree)

    for node in getattr(node_tree, "nodes", []):
        image = getattr(node, "image", None)
        if image is not None:
            _mark_owned(image)


def _mark_object_tree(obj: bpy.types.Object) -> None:
    if obj is None:
        return
    _mark_owned(obj)

    obj_data = getattr(obj, "data", None)
    if obj_data is not None:
        _mark_owned(obj_data)
        for material in getattr(obj_data, "materials", []):
            _mark_material_tree(material)
        node_tree = getattr(obj_data, "node_tree", None)
        if node_tree is not None:
            _mark_node_tree(node_tree)

    for slot in getattr(obj, "material_slots", []):
        _mark_material_tree(getattr(slot, "material", None))

    for modifier in getattr(obj, "modifiers", []):
        node_group = getattr(modifier, "node_group", None)
        if node_group is not None:
            _mark_node_tree(node_group)


def _normalize_modifier_input_name(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def _iter_modifier_group_inputs(modifier):
    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return []

    interface = getattr(node_group, "interface", None)
    items_tree = getattr(interface, "items_tree", None)
    if items_tree is not None:
        return [
            item
            for item in items_tree
            if getattr(item, "item_type", None) == "SOCKET"
            and getattr(item, "in_out", None) == "INPUT"
        ]

    return list(getattr(node_group, "inputs", []))


def _resolve_modifier_input_key(modifier, input_name: str) -> str:
    sockets = list(_iter_modifier_group_inputs(modifier))
    if not sockets:
        raise ValueError(f"Modifier '{modifier.name}' has no exposed inputs.")

    normalized_target = _normalize_modifier_input_name(input_name)
    modifier_keys = set(modifier.keys())
    matches: list[tuple[int, str, str]] = []

    for index, socket in enumerate(sockets, start=1):
        socket_name = str(getattr(socket, "name", ""))
        socket_identifier = str(getattr(socket, "identifier", ""))
        normalized_candidates = {
            _normalize_modifier_input_name(socket_name),
            _normalize_modifier_input_name(socket_identifier),
        }
        if normalized_target not in normalized_candidates:
            continue

        for candidate_key in (
            socket_identifier,
            f"Socket_{index}",
            f"Input_{index}",
        ):
            if candidate_key and candidate_key in modifier_keys:
                matches.append((index, socket_name, candidate_key))
                break

    if len(matches) == 1:
        return matches[0][2]
    if len(matches) > 1:
        matched = ", ".join(
            f"{socket_name} ({modifier.name})" for _, socket_name, _ in matches
        )
        raise ValueError(
            f"Input '{input_name}' is ambiguous across exposed modifier sockets: {matched}"
        )

    available = ", ".join(
        str(getattr(socket, "name", getattr(socket, "identifier", "")))
        for socket in sockets
    )
    raise ValueError(
        f"Modifier '{modifier.name}' has no input named '{input_name}'. "
        f"Available inputs: [{available}]"
    )


def _resolve_nodes_modifier(
    obj: bpy.types.Object,
    input_name: str | None = None,
    modifier_name: str | None = None,
):
    modifiers = list(getattr(obj, "modifiers", []))
    if modifier_name is not None:
        modifier = obj.modifiers.get(modifier_name)
        if modifier is None:
            available = ", ".join(mod.name for mod in modifiers)
            raise ValueError(
                f"Modifier '{modifier_name}' was not found on object '{obj.name}'. "
                f"Available modifiers: [{available}]"
            )
        if getattr(modifier, "type", None) != "NODES":
            raise ValueError(
                f"Modifier '{modifier_name}' is not a Geometry Nodes modifier."
            )
        return modifier

    nodes_modifiers = [
        modifier for modifier in modifiers if getattr(modifier, "type", None) == "NODES"
    ]
    if not nodes_modifiers:
        raise ValueError(f"Object '{obj.name}' has no Geometry Nodes modifiers.")
    if len(nodes_modifiers) == 1:
        return nodes_modifiers[0]
    if input_name is None:
        available = ", ".join(mod.name for mod in nodes_modifiers)
        raise ValueError(
            f"Object '{obj.name}' has multiple Geometry Nodes modifiers. "
            f"Specify modifier_name. Available modifiers: [{available}]"
        )

    matches = []
    for modifier in nodes_modifiers:
        try:
            _resolve_modifier_input_key(modifier, input_name)
        except ValueError:
            continue
        matches.append(modifier)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        available = ", ".join(mod.name for mod in matches)
        raise ValueError(
            f"Input '{input_name}' exists on multiple Geometry Nodes modifiers for "
            f"object '{obj.name}'. Specify modifier_name. Matching modifiers: [{available}]"
        )

    available = ", ".join(mod.name for mod in nodes_modifiers)
    raise ValueError(
        f"No Geometry Nodes modifier on object '{obj.name}' exposes input "
        f"'{input_name}'. Available modifiers: [{available}]"
    )


def _mark_world_tree(world) -> None:
    if world is None:
        return
    _mark_owned(world)
    node_tree = getattr(world, "node_tree", None)
    if node_tree is not None:
        _mark_node_tree(node_tree)


def _remove_owned_unused(id_collection) -> None:
    for datablock in list(id_collection):
        if not _is_owned(datablock):
            continue
        if getattr(datablock, "users", 0) > 0:
            continue
        try:
            id_collection.remove(datablock, do_unlink=True)
        except TypeError:
            id_collection.remove(datablock)


def _remove_rv_data() -> None:
    _get_generated_collection()
    scene = bpy.context.scene

    if scene.compositing_node_group is not None and _is_owned(
        scene.compositing_node_group
    ):
        scene.compositing_node_group = None

    for obj in list(bpy.data.objects):
        if not _is_owned(obj):
            continue
        bpy.data.objects.remove(obj, do_unlink=True)

    for world in list(bpy.data.worlds):
        if not _is_owned(world):
            continue
        if scene.world == world:
            scene.world = None
        bpy.data.worlds.remove(world, do_unlink=True)

    _remove_owned_unused(bpy.data.images)
    _remove_owned_unused(bpy.data.materials)
    _remove_owned_unused(bpy.data.meshes)
    _remove_owned_unused(bpy.data.node_groups)
    _remove_owned_unused(bpy.data.cameras)
    _remove_owned_unused(bpy.data.lights)
    _remove_owned_unused(bpy.data.curves)

    if scene.world is None:
        fallback_world = bpy.data.worlds.get("World")
        if fallback_world is None:
            fallback_world = bpy.data.worlds.new("World")
        scene.world = fallback_world


def _purge_orphans() -> None:
    # Blender API differs by version; attempt supported calls and keep cleanup best-effort.
    if not hasattr(bpy.data, "orphans_purge"):
        return

    try:
        bpy.data.orphans_purge(
            do_local_ids=True, do_linked_ids=False, do_recursive=True
        )
    except TypeError:
        try:
            bpy.data.orphans_purge()
        except Exception:
            pass
    except Exception:
        pass


def begin_run(
    purge_orphans: bool = True,  # Remove orphaned Blender datablocks after cleanup
) -> str:
    """
    Start a new rv run by clearing previously generated data and returning a new run ID.
    """
    global _ACTIVE_RUN_ID
    _remove_rv_data()
    if purge_orphans:
        _purge_orphans()
    _ACTIVE_RUN_ID = uuid.uuid4().hex
    return _ACTIVE_RUN_ID


def end_run(
    purge_orphans: bool = False,  # Remove orphaned Blender datablocks on shutdown
) -> None:
    """
    Finish the current rv run and optionally purge orphaned Blender datablocks.
    """
    if purge_orphans:
        _purge_orphans()


def _get_generated_collection() -> bpy.types.Collection:
    if "Generated" not in bpy.data.collections:
        bpy.data.collections.new("Generated")
    collection = bpy.data.collections["Generated"]
    if bpy.context.scene.collection.children.get(collection.name) is None:
        bpy.context.scene.collection.children.link(collection)
    return collection


def _move_object_to_generated_collection(obj: bpy.types.Object) -> None:
    generated = _get_generated_collection()
    for col in list(obj.users_collection):
        col.objects.unlink(obj)
    if generated.objects.get(obj.name) is None:
        generated.objects.link(obj)


class _Serializable:
    """
    Base class for objects that have metainformation saved in `_meta.json` file.
    """

    custom_meta: dict  # Custom metainformation that is not used by the framework but may be usefull when working with dataset later.

    def __init__(self):
        self.custom_meta = dict()

    def set_custom_meta(
        self, **custom_meta: Union[JSONSerializable, ObjectStats]
    ) -> None:
        """
        Set custom metainformation that may be helpful when using dataset later.
        """
        for key, value in custom_meta.items():
            if isinstance(value, ObjectStats):
                value = value.to_dict()
            self.custom_meta[key] = value

    def _get_meta(self) -> dict:
        return {
            "custom_meta": self.custom_meta,
        }


class Domain:
    """
    Scatter domain descriptor used by scene scattering methods.
    """

    kind: str  # Domain kind identifier (rect, ellipse, hull3d, etc.)
    data: dict  # Domain parameters required by sampling/containment logic
    dimension: int  # Domain dimensionality (2 for planar, 3 for volumetric)

    def __init__(self, kind: str, data: dict, dimension: int):
        self.kind = kind
        self.data = data
        self.dimension = dimension

    def inset(
        self,
        margin: float,  # Inset distance from the domain boundary
    ) -> "Domain":
        """
        Return a new domain shrunk inward by `margin`.
        """
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
        center: Float2 = (0.0, 0.0),  # XY center of the rectangle
        size: Float2 = (10.0, 10.0),  # Rectangle width and depth
        z: float = 0.0,  # Fixed Z plane for 2D scattering
    ) -> "Domain":
        """
        Build a rectangular 2D scatter domain.
        """
        _ensure_positive_tuple(size, 2, "size")
        return Domain("rect", {"center": tuple(center), "size": tuple(size), "z": z}, 2)

    @staticmethod
    def ellipse(
        center: Float2 = (0.0, 0.0),  # XY center of the ellipse
        radii: Float2 = (5.0, 3.0),  # Ellipse radii along X and Y
        z: float = 0.0,  # Fixed Z plane for 2D scattering
    ) -> "Domain":
        """
        Build an elliptical 2D scatter domain.
        """
        _ensure_positive_tuple(radii, 2, "radii")
        return Domain(
            "ellipse", {"center": tuple(center), "radii": tuple(radii), "z": z}, 2
        )

    @staticmethod
    def polygon(
        points: Polygon2D,  # Polygon vertices in XY
        z: float = 0.0,  # Fixed Z plane for 2D scattering
    ) -> "Domain":
        """
        Build a convex 2D scatter domain from polygon vertices.
        """
        if points is None or len(points) < 3:
            raise ValueError("polygon requires at least 3 points.")
        convex = _convex_hull_2d(points)
        if len(convex) < 3:
            raise ValueError("polygon is degenerate.")
        if _polygon_signed_area(convex) <= 0:
            convex = list(reversed(convex))
        return Domain("polygon", {"points": convex, "z": z}, 2)

    @staticmethod
    def box(
        center: Float3 = (0.0, 0.0, 0.0),  # 3D center
        size: Float3 = (10.0, 10.0, 10.0),  # Box side lengths
    ) -> "Domain":
        """
        Build an axis-aligned box scatter domain.
        """
        _ensure_positive_tuple(size, 3, "size")
        return Domain("box", {"center": tuple(center), "size": tuple(size)}, 3)

    @staticmethod
    def cylinder(
        center: Float3 = (0.0, 0.0, 0.0),  # Cylinder center
        radius: float = 5.0,  # Radial extent
        height: float = 10.0,  # Length along the selected axis
        axis: str = "Z",  # Longitudinal axis: X, Y, or Z
    ) -> "Domain":
        """
        Build a cylinder scatter domain aligned to X, Y, or Z.
        """
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
        center: Float3 = (0.0, 0.0, 0.0),  # Ellipsoid center
        radii: Float3 = (5.0, 3.0, 2.0),  # Radii along X, Y, Z
    ) -> "Domain":
        """
        Build an ellipsoid scatter domain.
        """
        _ensure_positive_tuple(radii, 3, "radii")
        return Domain("ellipsoid", {"center": tuple(center), "radii": tuple(radii)}, 3)

    @staticmethod
    def convex_hull(
        rv_obj: "Object",  # Source object to build the hull from
        project_2d: bool = False,  # If true, project hull to XY polygon
    ) -> "Domain":
        """
        Build a convex hull domain from an existing object.
        """
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

    def sample_point(self, rng: random.Random) -> mathutils.Vector:  # Random generator
        """
        Sample a random point inside this domain.
        """
        inset_margin = self._effective_inset_margin()

        if self.kind == "rect":
            cx, cy = self.data["center"]
            sx, sy = self.data["size"]
            half_x = sx * 0.5 - inset_margin
            half_y = sy * 0.5 - inset_margin
            if half_x <= 0 or half_y <= 0:
                raise ValueError("domain inset is too large to sample from rect.")
            z = self.data["z"]
            return Vector(
                (
                    rng.uniform(cx - half_x, cx + half_x),
                    rng.uniform(cy - half_y, cy + half_y),
                    z,
                )
            )

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
            return Vector(
                (
                    cx + rr * rx_in * math.cos(theta),
                    cy + rr * ry_in * math.sin(theta),
                    z,
                )
            )

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
            return Vector(
                (
                    rng.uniform(cx - hx, cx + hx),
                    rng.uniform(cy - hy, cy + hy),
                    rng.uniform(cz - hz, cz + hz),
                )
            )

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
                return Vector(
                    (cx + h, cy + rr * math.cos(theta), cz + rr * math.sin(theta))
                )
            if axis == "Y":
                return Vector(
                    (cx + rr * math.cos(theta), cy + h, cz + rr * math.sin(theta))
                )
            return Vector(
                (cx + rr * math.cos(theta), cy + rr * math.sin(theta), cz + h)
            )

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
            return Vector(
                (
                    cx + direction.x * rx_in * radial,
                    cy + direction.y * ry_in * radial,
                    cz + direction.z * rz_in * radial,
                )
            )

        if self.kind == "hull3d":
            aabb_min = Vector(self.data["aabb_min"])
            aabb_max = Vector(self.data["aabb_max"])
            for _ in range(512):
                p = Vector(
                    (
                        rng.uniform(aabb_min.x, aabb_max.x),
                        rng.uniform(aabb_min.y, aabb_max.y),
                        rng.uniform(aabb_min.z, aabb_max.z),
                    )
                )
                if self.contains_point(p, margin=0.0):
                    return p
            return Vector(self.data["centroid"])

        raise ValueError(f"Unsupported domain kind: {self.kind}")

    def contains_point(
        self,
        point: mathutils.Vector,  # Candidate point in world coordinates
        margin: float = 0.0,  # Inset margin from boundary
    ) -> bool:
        """
        Check whether a world-space point is inside the domain.
        """
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
            return (
                abs(point.x - cx) <= half_x + 1e-9
                and abs(point.y - cy) <= half_y + 1e-9
                and abs(point.z - self.data["z"]) <= 1e-6
            )

        if self.kind == "ellipse":
            cx, cy = self.data["center"]
            rx, ry = self.data["radii"]
            rx_in = rx - margin
            ry_in = ry - margin
            if rx_in <= 0 or ry_in <= 0:
                return False
            dx = (point.x - cx) / rx_in
            dy = (point.y - cy) / ry_in
            return (
                dx * dx + dy * dy <= 1.0 + 1e-9
                and abs(point.z - self.data["z"]) <= 1e-6
            )

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
            return (
                abs(point.x - cx) <= hx + 1e-9
                and abs(point.y - cy) <= hy + 1e-9
                and abs(point.z - cz) <= hz + 1e-9
            )

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

    def contains_object(
        self,
        obj: "Object",  # Object to validate against this domain
        margin: float = 0.0,  # Additional inset margin
        mode: Literal["aabb", "mesh"] = "mesh",  # Containment strategy
    ) -> bool:
        """
        Check whether an object is fully contained within this domain.
        """
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
        """
        Return the axis-aligned bounds of this domain.
        """
        inset_margin = self._effective_inset_margin()

        if self.kind == "rect":
            cx, cy = self.data["center"]
            sx, sy = self.data["size"]
            half_x = max(0.0, sx * 0.5 - inset_margin)
            half_y = max(0.0, sy * 0.5 - inset_margin)
            z = self.data["z"]
            return Vector((cx - half_x, cy - half_y, z)), Vector(
                (cx + half_x, cy + half_y, z)
            )

        if self.kind == "ellipse":
            cx, cy = self.data["center"]
            rx, ry = self.data["radii"]
            rx_in = max(0.0, rx - inset_margin)
            ry_in = max(0.0, ry - inset_margin)
            z = self.data["z"]
            return Vector((cx - rx_in, cy - ry_in, z)), Vector(
                (cx + rx_in, cy + ry_in, z)
            )

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
            return Vector((cx - hx, cy - hy, cz - hz)), Vector(
                (cx + hx, cy + hy, cz + hz)
            )

        if self.kind == "cylinder":
            cx, cy, cz = self.data["center"]
            r = max(0.0, self.data["radius"] - inset_margin)
            h = max(0.0, self.data["height"] * 0.5 - inset_margin)
            axis = self.data["axis"]
            if axis == "X":
                return Vector((cx - h, cy - r, cz - r)), Vector(
                    (cx + h, cy + r, cz + r)
                )
            if axis == "Y":
                return Vector((cx - r, cy - h, cz - r)), Vector(
                    (cx + r, cy + h, cz + r)
                )
            return Vector((cx - r, cy - r, cz - h)), Vector((cx + r, cy + r, cz + h))

        if self.kind == "ellipsoid":
            cx, cy, cz = self.data["center"]
            rx, ry, rz = self.data["radii"]
            rx_in = max(0.0, rx - inset_margin)
            ry_in = max(0.0, ry - inset_margin)
            rz_in = max(0.0, rz - inset_margin)
            return Vector((cx - rx_in, cy - ry_in, cz - rz_in)), Vector(
                (cx + rx_in, cy + ry_in, cz + rz_in)
            )

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
            return (
                math.floor(point.x / self.cell_size),
                math.floor(point.y / self.cell_size),
            )
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
                    result.extend(
                        self.cells.get((base[0] + dx, base[1] + dy, base[2] + dz), [])
                    )
        return result


class Scene(ABC, _Serializable):
    """
    Base class for describing rv scene. To set up a scene, implement `generate` function.
    """

    resolution: Resolution = (640, 640)  # Output image resolution (width, height)
    time_limit: float = 3.0  # Per-frame render time limit in seconds
    passes: RenderPassSet = None  # Enabled auxiliary render passes
    output_dir: Optional[
        str
    ]  # Directory for storing all outputs generated by a single `rv render` run
    subdir: str  # Directory to store results of a single rendering
    camera: "Camera"  # Scene camera wrapper
    world: "World"  # Active environment lighting descriptor
    tags: TagSet  # Scene-level classification tags

    objects: set["Object"]  # Registered scene objects
    materials: set["Material"]  # Registered material descriptors
    lights: set["Light"]  # Registered lights
    semantic_channels: (
        SemanticChannelSet  # Semantic mask channels exported from shader AOVs
    )
    semantic_mask_threshold: float = 0.5  # Binary threshold for semantic masks

    object_index_counter: int = 0  # Monotonic object pass-index counter
    material_index_counter: int = 0  # Monotonic material pass-index counter
    light_index_counter: int = 0  # Monotonic light index counter

    @abstractmethod
    def generate(self) -> None:
        """
        Method to describe scene generation. To use framework you must implement it in a derrived class.
        """
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

        self.world = SkyWorld()

    def set_rendering_time_limit(
        self,
        time_limit: float = 3.0,  # Rendering time limit in seconds
    ):
        """
        Set the maximum allowed rendering time for a single image. Higher value leads to better quality.
        """
        self.time_limit = time_limit
        return self

    def set_passes(
        self,
        *passes: tuple[RenderPass | list[RenderPass], ...],  # Render passes to enable
    ):
        """
        Set a list of render passes that will be saved when rendering.
        """
        self.passes = _combine_arglist_set(passes)
        return self

    def enable_semantic_channels(
        self,
        *channels: tuple[
            str | list[str], ...
        ],  # Semantic channel names written via AOVs
    ) -> "Scene":
        """
        Enable semantic shader channels to be exported as masks.
        In Blender node graphs, write channel values to AOV outputs named `<channel>`.
        """
        for channel in _combine_arglist_set(channels):
            self.semantic_channels.add(_normalize_semantic_channel(channel))
        return self

    def set_semantic_mask_threshold(
        self,
        threshold: float,  # Binary mask threshold in [0, 1]
    ) -> "Scene":
        """
        Set threshold used when exporting binary semantic masks.
        """
        if threshold < 0.0 or threshold > 1.0:
            raise ValueError("semantic mask threshold must be in [0, 1].")
        self.semantic_mask_threshold = threshold
        return self

    def create_empty(
        self,
        name: str = "Empty",  # Object name
    ) -> "Object":
        """
        Create an empty object. May be useful to point camera at or for debugging during `preview` stage.
        """
        empty = bpy.data.objects.new(name, None)
        _mark_object_tree(empty)
        _get_generated_collection().objects.link(empty)

        return Object(empty, self)

    def create_sphere(
        self,
        name: str = "Sphere",  # Object name
        radius: float = 1.0,  # Sphere radius
        segments: int = 32,  # Horizontal segments
        ring_count: int = 16,  # Vertical segments
    ) -> "Object":
        """
        Create a sphere primitive.
        """
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=radius, segments=segments, ring_count=ring_count
        )
        sphere = bpy.context.active_object
        _move_object_to_generated_collection(sphere)
        _mark_object_tree(sphere)
        sphere.name = name
        return Object(sphere, self)

    def create_cube(
        self,
        name: str = "Cube",  # Object name
        size: float = 2.0,  # Cube side size
    ) -> "Object":
        """
        Create a cube primitive.
        """
        bpy.ops.mesh.primitive_cube_add(size=size)
        cube = bpy.context.active_object
        _move_object_to_generated_collection(cube)
        _mark_object_tree(cube)
        cube.name = name
        return Object(cube, self)

    def create_plane(
        self,
        name: str = "Plane",  # Object name
        size: float = 2.0,  # Plane side size
    ) -> "Object":
        """
        Create a plane primitive.
        """
        bpy.ops.mesh.primitive_plane_add(
            size=size,
        )
        plane = bpy.context.active_object
        _move_object_to_generated_collection(plane)
        _mark_object_tree(plane)
        plane.name = name
        return Object(plane, self)

    def create_point_light(
        self,
        name: str = "Point",  # Light object name
        power: float = 1000.0,  # Light power in Blender energy units
    ) -> "PointLight":
        """
        Create a point light.
        """
        light_data = bpy.data.lights.new(name=name, type="POINT")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return PointLight(light_obj, self).set_power(power)

    def create_sun_light(
        self,
        name: str = "Sun",  # Light object name
        power: float = 1.0,  # Light power in Blender energy units
    ) -> "SunLight":
        """
        Create a sun light.
        """
        light_data = bpy.data.lights.new(name=name, type="SUN")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return SunLight(light_obj, self).set_power(power)

    def create_area_light(
        self,
        name: str = "Area",  # Light object name
        power: float = 100.0,  # Light power in Blender energy units
    ) -> "AreaLight":
        """
        Create an area light.
        """
        light_data = bpy.data.lights.new(name=name, type="AREA")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return AreaLight(light_obj, self).set_power(power)

    def create_spot_light(
        self,
        name: str = "Spot",  # Light object name
        power: float = 1000.0,  # Light power in Blender energy units
    ) -> "SpotLight":
        """
        Create a spot light.
        """
        light_data = bpy.data.lights.new(name=name, type="SPOT")
        light_obj = bpy.data.objects.new(name, light_data)
        _mark_object_tree(light_obj)
        _get_generated_collection().objects.link(light_obj)
        return SpotLight(light_obj, self).set_power(power)

    def get_camera(self) -> "Camera":
        """
        Get the `Camera` object used for rendering.
        """
        return self.camera

    def set_world(
        self,
        world: "World",  # World descriptor to apply to the scene
    ) -> "World":
        """
        Set a new `World` representing environmental lighting.
        """
        self.world = world
        return world

    def get_world(self) -> "World":
        """
        Get current used `World`.
        """
        return self.world

    def set_tags(
        self,
        *tags,  # Scene-level tags
    ) -> "Scene":
        """
        Set scene's global tags.

        Tags are used to represent image class for training a computer vision model for a classification task.
        """
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(
        self,
        *tags,  # Tags to append to scene-level tags
    ) -> "Scene":
        """
        Add tags to the scene.

        Tags are used to represent image class for training a computer vision model for a classification task.
        """
        self.tags |= _combine_arglist_set(tags)
        return self

    def load_object(
        self,
        blendfile: str,  # Path to source .blend file
        import_name: str = None,  # Optional object name to import
    ) -> "ObjectLoader":
        """
        Get a loader object to import from a blender file.

        If `import_name` is specified, it imports an object with specified name.
        If no `import_name` is specified, it imports the first object.

        Loader object is used to create instances of an object.
        """

        path = str(pathlib.Path(blendfile).expanduser())

        if import_name is None:
            obj = _load_single_object(path)
            _mark_object_tree(obj)
            return ObjectLoader(obj, self)
        else:
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

    def load_objects(
        self,
        blendfile: str,  # Path to source .blend file
        import_names: list[str] = None,  # Optional list of object names to import
    ) -> list["ObjectLoader"]:
        """
        Get a list of loader objects to import from a blender file.

        If `import_names` is specified, it imports only specified objects.
        If no `import_names` is specified, it imports all specfied objects.

        Loader object is used to create instances of an object.
        """
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

    def create_material(
        self,
        name: str = "Material",  # Material name
    ) -> "BasicMaterial":
        """
        Create a new basic (Principled BSDF) material.
        """
        return BasicMaterial(name=name)

    def import_material(
        self,
        blendfile: str,  # Path to source .blend file
        material_name: str = None,  # Material name to import (defaults to first)
    ) -> "ImportedMaterial":
        """
        Create an imported material descriptor from a .blend file.
        """
        path = str(pathlib.Path(blendfile).expanduser())
        return ImportedMaterial(filepath=path, material_name=material_name)

    def inspect_object(
        self,
        loader_or_obj: Union["ObjectLoader", "Object"],  # Object or loader to inspect
        applied_scale: bool = True,  # Include object scale in reported local dimensions
    ) -> ObjectStats:
        """
        Inspect geometric stats for a loader/object without manual .blend inspection.
        """
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

    def scatter_by_sphere(
        self,
        source: ObjectLoaderSource,  # Source loader(s)
        count: int,  # Requested number of objects to place
        domain: "Domain",  # Scatter domain descriptor
        min_gap: float = 0.0,  # Extra spacing between placed objects
        yaw_range: Float2 = (0.0, 360.0),  # Yaw range in degrees
        rotation_mode: Literal["yaw", "free"] = "yaw",  # Rotation sampling strategy
        scale_range: Float2 = (1.0, 1.0),  # Uniform scale range
        max_attempts_per_object: int = 100,  # Retry budget per requested object
        boundary_mode: Literal["center_margin"] = "center_margin",  # Boundary policy
        boundary_margin: float = 0.0,  # Required inset distance from domain edge
        seed: int | None = None,  # RNG seed for deterministic sampling
    ) -> list["Object"]:
        """
        Scatter objects using bounding-sphere collisions.
        """
        loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(
            source=source,
            count=count,
            domain=domain,
            min_gap=min_gap,
            yaw_range=yaw_range,
            rotation_mode=rotation_mode,
            scale_range=scale_range,
            max_attempts_per_object=max_attempts_per_object,
            boundary_mode=boundary_mode,
            boundary_margin=boundary_margin,
        )

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

                rot = _sample_rotation_quaternion(
                    rng=rng,
                    domain_dimension=domain.dimension,
                    rotation_mode=rotation_mode,
                    yaw_min=yaw_min,
                    yaw_max=yaw_max,
                )
                radius = base_radii[loader_idx] * scale
                neighbors = grid.neighbors(pos)
                if _overlaps_by_radius(
                    position=pos,
                    radius=radius,
                    neighbors=neighbors,
                    placed_infos=placed_infos,
                    dimension=domain.dimension,
                    min_gap=min_gap,
                ):
                    stats["rejected_overlap"] += 1
                    continue

                obj = loader.create_instance()
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                placed.append(obj)
                placed_infos.append(
                    {"position": Vector(pos), "radius": radius, "object": obj}
                )
                grid.insert(pos, len(placed_infos) - 1)
                placed_one = True
                break

            if not placed_one:
                stats["rejected_attempt_limit"] += 1

        _finalize_scatter_stats(self, stats=stats, placed=placed, requested=count)
        return placed

    def scatter_by_bvh(
        self,
        source: ObjectLoaderSource,  # Source loader(s)
        count: int,  # Requested number of objects to place
        domain: "Domain",  # Scatter domain descriptor
        min_gap: float = 0.0,  # Extra spacing between placed objects
        yaw_range: Float2 = (0.0, 360.0),  # Yaw range in degrees
        rotation_mode: Literal["yaw", "free"] = "yaw",  # Rotation sampling strategy
        scale_range: Float2 = (1.0, 1.0),  # Uniform scale range
        max_attempts_per_object: int = 100,  # Retry budget per requested object
        boundary_mode: Literal["center_margin"] = "center_margin",  # Boundary policy
        boundary_margin: float = 0.0,  # Required inset distance from domain edge
        seed: int | None = None,  # RNG seed for deterministic sampling
    ) -> list["Object"]:
        """
        Scatter objects using exact BVH overlap checks with broad-phase pruning.
        """
        loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(
            source=source,
            count=count,
            domain=domain,
            min_gap=min_gap,
            yaw_range=yaw_range,
            rotation_mode=rotation_mode,
            scale_range=scale_range,
            max_attempts_per_object=max_attempts_per_object,
            boundary_mode=boundary_mode,
            boundary_margin=boundary_margin,
        )

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

                rot = _sample_rotation_quaternion(
                    rng=rng,
                    domain_dimension=domain.dimension,
                    rotation_mode=rotation_mode,
                    yaw_min=yaw_min,
                    yaw_max=yaw_max,
                )
                radius = base_radii[loader_idx] * scale
                neighbors = grid.neighbors(pos)
                if _overlaps_by_radius(
                    position=pos,
                    radius=radius,
                    neighbors=neighbors,
                    placed_infos=placed_infos,
                    dimension=domain.dimension,
                    min_gap=min_gap,
                ):
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
                placed_infos.append(
                    {"position": Vector(pos), "radius": radius, "object": obj}
                )
                grid.insert(pos, len(placed_infos) - 1)
                placed_one = True
                break

            if not placed_one:
                stats["rejected_attempt_limit"] += 1

        _finalize_scatter_stats(self, stats=stats, placed=placed, requested=count)
        return placed

    def scatter_parametric(
        self,
        source: "ParametricSource",  # Parameterized source descriptor
        count: int,  # Requested number of objects to place
        domain: "Domain",  # Scatter domain descriptor
        strategy: Literal["sphere", "bvh"] = "sphere",  # Collision strategy
        min_gap: float = 0.0,  # Extra spacing between placed objects
        yaw_range: Float2 = (0.0, 360.0),  # Yaw range in degrees
        rotation_mode: Literal["yaw", "free"] = "yaw",  # Rotation sampling strategy
        scale_range: Float2 = (1.0, 1.0),  # Uniform scale range
        max_attempts_per_object: int = 100,  # Retry budget per requested object
        boundary_mode: Literal["center_margin"] = "center_margin",  # Boundary policy
        boundary_margin: float = 0.0,  # Required inset distance from domain edge
        seed: int | None = None,  # RNG seed for deterministic sampling
    ) -> list["Object"]:
        """
        Scatter parameterized objects. Dimensions are measured on candidate geometry per attempt.
        """
        if not isinstance(source, ParametricSource):
            raise TypeError("source must be ParametricSource.")
        if strategy not in {"sphere", "bvh"}:
            raise ValueError("strategy must be one of: sphere, bvh.")

        _loaders, scale_min, scale_max, yaw_min, yaw_max = _validate_scatter_common(
            source=source.source,
            count=count,
            domain=domain,
            min_gap=min_gap,
            yaw_range=yaw_range,
            rotation_mode=rotation_mode,
            scale_range=scale_range,
            max_attempts_per_object=max_attempts_per_object,
            boundary_mode=boundary_mode,
            boundary_margin=boundary_margin,
        )

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
                rot = _sample_rotation_quaternion(
                    rng=rng,
                    domain_dimension=domain.dimension,
                    rotation_mode=rotation_mode,
                    yaw_min=yaw_min,
                    yaw_max=yaw_max,
                )

                temp_obj = source.create_instance(params=params, register_object=False)
                temp_obj.set_scale(scale).set_rotation(rot).set_location(pos)
                radius = _object_world_radius(temp_obj.obj, domain.dimension)
                # Radius depends on sampled params, so use full-set checks for correctness.
                neighbors = list(range(len(placed_infos)))
                if _overlaps_by_radius(
                    position=pos,
                    radius=radius,
                    neighbors=neighbors,
                    placed_infos=placed_infos,
                    dimension=domain.dimension,
                    min_gap=min_gap,
                ):
                    _remove_blender_object(temp_obj.obj)
                    stats["rejected_overlap"] += 1
                    continue

                if strategy == "bvh":
                    neighbor_objs = [
                        placed_infos[idx]["object"].obj for idx in neighbors
                    ]
                    if _mesh_object_overlaps_any(temp_obj.obj, neighbor_objs):
                        _remove_blender_object(temp_obj.obj)
                        stats["rejected_overlap"] += 1
                        continue
                _remove_blender_object(temp_obj.obj)

                obj = source.create_instance(params=params, register_object=True)
                obj.set_scale(scale).set_rotation(rot).set_location(pos)
                placed.append(obj)
                placed_infos.append(
                    {
                        "position": Vector(pos),
                        "radius": radius,
                        "object": obj,
                        "params": params,
                    }
                )
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
            _configure_compositor(
                None,
                semantic_channels=self.semantic_channels,
                semantic_mask_threshold=self.semantic_mask_threshold,
            )
        else:
            if self.subdir is None:
                self.subdir = str(uuid.uuid4())
            _configure_compositor(
                os.path.join(self.output_dir, self.subdir),
                semantic_channels=self.semantic_channels,
                semantic_mask_threshold=self.semantic_mask_threshold,
            )

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


class ObjectLoader:
    """
    Helper for creating object instances from a loaded Blender object source.
    """

    def __init__(self, obj, scene: "Scene") -> None:
        self.obj = obj
        self.scene = scene

    def set_source(
        self,
        source: "Object",  # Object used as instancing prototype
    ) -> "ObjectLoader":
        """
        Rebind this loader to use an existing object as its instancing prototype.
        """
        if not isinstance(source, Object):
            raise TypeError("source must be Object.")
        if source.scene is not self.scene:
            raise ValueError("source object must belong to the same scene.")
        self.obj = source.obj
        return self

    def create_instance(
        self,
        name: str = None,  # Instanced object name
        register_object: bool = True,  # Register in scene metadata/indexes
    ) -> "Object":
        """
        Create a single object instance from a loader.
        """
        res = self.obj.copy()
        _mark_object_tree(res)
        _get_generated_collection().objects.link(res)

        if name is not None:
            res.name = name

        return Object(res, self.scene, register_object=register_object)


class ParametricSource:
    """
    Source wrapper for parameterized scattering.

    It can sample parameters per candidate and apply them to each created instance.
    """

    def __init__(self, source: ObjectLoader) -> None:
        self.source = source
        self._sampler: typing.Callable[[random.Random], dict] | None = None
        self._applier: typing.Callable[["Object", dict], None] | None = None

    def set_sampler(
        self,
        sampler: typing.Callable[
            [random.Random], dict
        ],  # Samples a params dict from RNG
    ) -> "ParametricSource":
        """
        Set a callback that samples a parameter dictionary for each candidate.
        """
        self._sampler = sampler
        return self

    def set_applier(
        self,
        applier: typing.Callable[
            ["Object", dict], None
        ],  # Applies params to created object
    ) -> "ParametricSource":
        """
        Set a callback that applies sampled parameters to the created object.
        """
        self._applier = applier
        return self

    def sample_params(self, rng: random.Random) -> dict:  # Random generator
        if self._sampler is None:
            return {}
        params = self._sampler(rng)
        if params is None:
            return {}
        if not isinstance(params, dict):
            raise TypeError("ParametricSource sampler must return a dict.")
        return params

    def create_instance(
        self,
        params: dict | None = None,  # Sampled parameter dictionary
        register_object: bool = True,  # Register in scene metadata/indexes
        name: str = None,  # Instance object name
    ) -> "Object":
        obj = self.source.create_instance(name=name, register_object=register_object)
        if params is None:
            params = {}
        if not isinstance(params, dict):
            raise TypeError("params must be a dict.")
        for key, value in params.items():
            obj.set_property(key, value)
        if self._applier is not None:
            self._applier(obj, params)
        return obj


class Material(ABC, _Serializable):
    """
    Base class for material descriptors.

    A material descriptor is converted to a real Blender material when assigned to an object.
    """

    name: str | None  # Material display name
    index: int | None  # Assigned material pass index in the scene
    _resolved_material: bpy.types.Material | None  # Cached built Blender material

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self.name = name
        self.index = None
        self._resolved_material = None

    @abstractmethod
    def set_params(self, **kwargs):
        """
        Update descriptor-specific material parameters and return `self`.
        """
        pass

    @abstractmethod
    def _build_material(self) -> bpy.types.Material:
        pass

    def _resolve(self, scene: "Scene") -> bpy.types.Material:
        if self._resolved_material is not None:
            try:
                resolved_name = self._resolved_material.name
                if bpy.data.materials.get(resolved_name) == self._resolved_material:
                    return self._resolved_material
            except Exception:
                pass
            self._resolved_material = None

        material = self._build_material()
        _mark_material_tree(material)
        self.index = scene._register_material(self)
        material.pass_index = self.index
        self._resolved_material = material
        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "type": self.__class__.__name__,
                "index": self.index,
                "name": (
                    self._resolved_material.name
                    if self._resolved_material is not None
                    else self.name
                ),
            }
        )
        return res


def _get_principled_bsdf_node(material: bpy.types.Material):
    node_tree = getattr(material, "node_tree", None)
    if node_tree is None:
        return None
    for node in node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def _normalize_semantic_channel(channel: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in channel).strip(
        "_"
    )
    if normalized == "":
        raise ValueError(
            "semantic channel must contain at least one alphanumeric char."
        )
    return normalized


def _semantic_aov_name(channel: str) -> str:
    return _normalize_semantic_channel(channel)


class BasicMaterial(Material):
    """
    Material descriptor backed by Blender's Principled BSDF shader.
    """

    base_color: ColorRGBA | None  # Principled base RGBA color
    roughness: float | None  # Surface roughness
    metallic: float | None  # Metallic factor
    specular: float | None  # Specular IOR level
    emission_color: ColorRGBA | None  # Emission RGBA color
    emission_strength: float | None  # Emission intensity
    alpha: float | None  # Surface alpha/transparency
    transmission: float | None  # Transmission weight
    ior: float | None  # Index of refraction
    properties: dict  # Custom Blender properties to set on the material

    def __init__(self, name: str = "Material"):
        super().__init__(name=name)
        self.base_color = None
        self.roughness = None
        self.metallic = None
        self.specular = None
        self.emission_color = None
        self.emission_strength = None
        self.alpha = None
        self.transmission = None
        self.ior = None
        self.properties = dict()

    def set_params(
        self,
        base_color: OptionalColor = None,  # Base color (RGB/RGBA)
        roughness: float = None,  # Surface roughness
        metallic: float = None,  # Metallic factor
        specular: float = None,  # Specular IOR level
        emission_color: OptionalColor = None,  # Emission color (RGB/RGBA)
        emission_strength: float = None,  # Emission intensity
        alpha: float = None,  # Alpha/transparency
        transmission: float = None,  # Transmission weight
        ior: float = None,  # Index of refraction
    ):
        """
        Set Principled BSDF parameters used when building the material.
        """

        def _as_rgba(
            color: Color,
        ) -> ColorRGBA:
            rgba = tuple(color)
            if len(rgba) == 3:
                return (rgba[0], rgba[1], rgba[2], 1.0)
            if len(rgba) != 4:
                raise TypeError("Color must have 3 (RGB) or 4 (RGBA) components.")
            return rgba

        if base_color is not None:
            self.base_color = _as_rgba(base_color)
        if roughness is not None:
            self.roughness = roughness
        if metallic is not None:
            self.metallic = metallic
        if specular is not None:
            self.specular = specular
        if emission_color is not None:
            self.emission_color = _as_rgba(emission_color)
        if emission_strength is not None:
            self.emission_strength = emission_strength
        if alpha is not None:
            self.alpha = alpha
        if transmission is not None:
            self.transmission = transmission
        if ior is not None:
            self.ior = ior
        return self

    def set_property(
        self,
        key: str,  # Custom property key
        value: any,  # Custom property value
    ):
        """
        Set a custom Blender property on the generated material.
        """
        self.properties[key] = value
        return self

    def _build_material(self) -> bpy.types.Material:
        material = bpy.data.materials.new(name=self.name or "Material")
        material.use_nodes = True

        node = _get_principled_bsdf_node(material)
        if node is None:
            raise RuntimeError("Failed to create a Principled BSDF node.")

        if self.base_color is not None:
            node.inputs["Base Color"].default_value = self.base_color
        if self.roughness is not None:
            node.inputs["Roughness"].default_value = self.roughness
        if self.metallic is not None:
            node.inputs["Metallic"].default_value = self.metallic
        if self.specular is not None:
            node.inputs["Specular IOR Level"].default_value = self.specular
        if self.emission_color is not None:
            node.inputs["Emission Color"].default_value = self.emission_color
        if self.emission_strength is not None:
            node.inputs["Emission Strength"].default_value = self.emission_strength
        if self.alpha is not None:
            node.inputs["Alpha"].default_value = self.alpha
            material.blend_method = "BLEND" if self.alpha < 1.0 else "OPAQUE"
        if self.transmission is not None:
            node.inputs["Transmission Weight"].default_value = self.transmission
        if self.ior is not None:
            node.inputs["IOR"].default_value = self.ior

        for key, value in self.properties.items():
            material[key] = value

        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "params": {
                    "base_color": self.base_color,
                    "roughness": self.roughness,
                    "metallic": self.metallic,
                    "specular": self.specular,
                    "emission_color": self.emission_color,
                    "emission_strength": self.emission_strength,
                    "alpha": self.alpha,
                    "transmission": self.transmission,
                    "ior": self.ior,
                },
                "properties": self.properties,
            }
        )
        return res


class ImportedMaterial(Material):
    """
    Material descriptor that imports a material from another `.blend` file.
    """

    filepath: str  # Source .blend file path
    material_name: str | None  # Material name inside the .blend file
    params: dict  # Custom properties to apply after import

    def __init__(self, filepath: str, material_name: str = None):
        super().__init__(name=material_name)
        self.filepath = filepath
        self.material_name = material_name
        self.params = dict()

    def set_params(self, **kwargs):
        """
        Set custom properties applied to the imported material.
        """
        self.params.update(kwargs)
        return self

    def _build_material(self) -> bpy.types.Material:
        with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
            if self.material_name is None:
                if len(data_from.materials) == 0:
                    raise ValueError(f"No materials found in '{self.filepath}'.")
                data_to.materials = [data_from.materials[0]]
            else:
                if self.material_name not in data_from.materials:
                    available = ", ".join(data_from.materials)
                    raise ValueError(
                        f"Material '{self.material_name}' was not found in '{self.filepath}'. "
                        f"Available materials: [{available}]"
                    )
                data_to.materials = [self.material_name]

        material = data_to.materials[0]
        for key, value in self.params.items():
            material[key] = value
        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "filepath": self.filepath,
                "material_name": self.material_name,
                "params": self.params,
            }
        )
        return res


class Object(_Serializable):
    """
    Wrapper around a Blender object with chainable transformation and metadata helpers.
    """

    obj: bpy.types.Object  # Underlying Blender object
    scene: Scene  # Owning scene
    tags: TagSet  # Object-level semantic tags
    properties: dict  # Custom properties assigned to this object
    modifier_parameters: list[dict[str, JSONSerializable]]  # Saved Geometry Nodes modifier parameters

    index: int | None  # Assigned object pass index

    def __init__(
        self, obj: bpy.types.Object, scene: "Scene", register_object: bool = True
    ) -> None:
        super().__init__()

        self.obj = obj
        self.scene = scene

        self.tags = set()
        self.properties = dict()
        self.modifier_parameters = []
        exported_meta = _restore_rv_export_object_metadata(self.obj)
        if isinstance(exported_meta.get("tags"), list):
            self.tags = set(
                tag for tag in exported_meta["tags"] if isinstance(tag, str)
            )
        if isinstance(exported_meta.get("properties"), dict):
            self.properties = dict(exported_meta["properties"])
        self.modifier_parameters = _restore_modifier_parameters(
            exported_meta.get("modifier_parameters")
        )
        if isinstance(exported_meta.get("custom_meta"), dict):
            self.custom_meta = dict(exported_meta["custom_meta"])

        self.index = None
        if register_object:
            self.index = self.scene._register_object(self)
            self.obj.pass_index = self.index
        self.obj.rotation_mode = "QUATERNION"

    def set_location(
        self,
        location: Union[
            mathutils.Vector, typing.Sequence[float]
        ],  # Object location in world coordinates
    ):
        """
        Set the location of the object in 3D space.
        """
        if isinstance(location, mathutils.Vector):
            self.obj.location = location
        elif len(location) != 3:
            raise TypeError()
        else:
            self.obj.location = mathutils.Vector(location)

        return self

    def set_rotation(
        self,
        rotation: Union[mathutils.Euler, mathutils.Quaternion],  # Object rotation value
    ):
        """
        Set the rotation of the object.
        """
        if isinstance(rotation, mathutils.Euler):
            self.obj.rotation_quaternion = rotation.to_quaternion()
        elif isinstance(rotation, mathutils.Quaternion):
            self.obj.rotation_quaternion = rotation
        else:
            raise TypeError()
        return self

    def set_scale(
        self,
        scale: Union[
            mathutils.Vector, typing.Sequence[float], float, int
        ],  # Uniform scalar or per-axis XYZ scale
    ):
        """
        Set the scale of the object.

        If `scale` is a single numeric value, all axes are set to that value.
        If `scale` is a sequence or Vector of length 3, each axis is set individually.
        """
        if isinstance(scale, mathutils.Vector):
            self.obj.scale = scale
        elif isinstance(scale, numbers.Real) and not isinstance(scale, bool):
            self.obj.scale = mathutils.Vector((scale, scale, scale))
        elif len(scale) == 3:
            self.obj.scale = mathutils.Vector(scale)
        else:
            raise TypeError()

        return self

    def set_property(
        self,
        key: str,  # Custom property key
        value: any,  # Custom property value
    ):
        """
        Set a property of the object. Properties can be used inside object's material nodes.
        """
        self.obj[key] = value
        self.properties[key] = value
        return self

    def set_modifier_input(
        self,
        input_name: str,  # Exposed modifier input name or identifier
        value: any,  # Value assigned to the modifier input
        modifier_name: (
            str | None
        ) = None,  # Optional modifier name when disambiguation is needed
    ):
        """
        Set an exposed Geometry Nodes modifier input.

        If `modifier_name` is omitted, `rv` searches for a unique Geometry Nodes
        modifier that exposes the requested input.
        """
        modifier = _resolve_nodes_modifier(
            self.obj, input_name=input_name, modifier_name=modifier_name
        )
        input_key = _resolve_modifier_input_key(modifier, input_name)
        modifier[input_key] = value
        for parameter in self.modifier_parameters:
            if (
                parameter["modifier_name"] == modifier.name
                and parameter["parameter_name"] == input_name
            ):
                parameter["value"] = value
                break
        else:
            self.modifier_parameters.append(
                {
                    "modifier_name": modifier.name,
                    "parameter_name": input_name,
                    "value": value,
                }
            )
        _mark_node_tree(getattr(modifier, "node_group", None))
        return self

    def set_material(
        self,
        material: "Material",  # Material descriptor to assign
        slot: int = 0,  # Material slot index
    ):
        """
        Set object material in the given slot.
        """
        if self.obj.data is None or not hasattr(self.obj.data, "materials"):
            raise TypeError("Object does not support materials.")
        if slot < 0:
            raise ValueError("Material slot index must be non-negative.")

        bpy_material = material._resolve(self.scene)
        materials = self.obj.data.materials
        while len(materials) <= slot:
            materials.append(None)
        materials[slot] = bpy_material
        _mark_material_tree(bpy_material)
        return self

    def add_material(
        self,
        material: "Material",  # Material descriptor to append
    ):
        """
        Append material to object's material slots.
        """
        if self.obj.data is None or not hasattr(self.obj.data, "materials"):
            raise TypeError("Object does not support materials.")
        bpy_material = material._resolve(self.scene)
        self.obj.data.materials.append(bpy_material)
        _mark_material_tree(bpy_material)
        return self

    def clear_materials(self):
        """
        Remove all materials from object.
        """
        if self.obj.data is None or not hasattr(self.obj.data, "materials"):
            raise TypeError("Object does not support materials.")
        self.obj.data.materials.clear()
        return self

    def set_tags(
        self,
        *tags: str | list[str],  # Object-level tags
    ):
        """
        Set object's tags.

        Tags are used to represent object class for training a computer vision model. Object can have more then one tag.
        """
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(
        self,
        *tags: str | list[str],  # Tags to append to object-level tags
    ):
        """
        Add tags to the object.

        Tags are used to represent object class for training a computer vision model. Object can have more then one tag.
        """
        self.tags |= _combine_arglist_set(tags)
        return self

    def point_at(
        self,
        rv_obj: "Object",  # Object to point at
        angle: float = 0.0,  # Angle to rotate around the direction vector in degrees
    ):
        """
        Orients the current object to point at another object, with an optional rotation around the direction vector.
        """
        direction = rv_obj.obj.location - self.obj.location
        rot_quat = direction.to_track_quat("-Z", "Y")
        if angle != 0.0:
            axis = direction.normalized()
            angle_quat = mathutils.Quaternion(axis, math.radians(angle))
            rot_quat = angle_quat @ rot_quat
        self.obj.rotation_quaternion = rot_quat
        return self

    def rotate_around_axis(
        self,
        axis: mathutils.Vector,  # Axis of rotation
        angle: float,  # Angle of rotation in degrees
    ):
        """
        Rotate object around an axis.
        """
        rot_quat = mathutils.Quaternion(axis, math.radians(angle))
        self.obj.rotation_quaternion = rot_quat @ self.obj.rotation_quaternion
        return self

    def _select_for_shading_ops(self) -> None:
        bpy.ops.object.select_all(action="DESELECT")
        self.obj.select_set(True)
        bpy.context.view_layer.objects.active = self.obj

    def set_shading(
        self,
        shading: Literal["flat", "smooth", "auto"],  # Target shading mode
    ):
        """
        Set shading to flat, smooth, or auto.
        """
        self._select_for_shading_ops()

        if shading == "flat":
            bpy.ops.object.shade_flat()
        elif shading == "smooth":
            bpy.ops.object.shade_smooth()
        elif shading == "auto":
            bpy.ops.object.shade_auto_smooth()
        else:
            raise ValueError(f"Unknown shading mode: {shading}")

        return self

    def show_debug_axes(
        self,
        show=True,  # Toggle axis visibility in preview
    ):
        """
        Show debug axes that can be seen in the `preview` mode.
        """
        self.obj.show_axis = show
        return self

    def show_debug_name(
        self,
        show,  # Toggle object-name visibility in preview
    ):
        """
        Show object's name that can be seen in the `preview` mode.
        """
        self.obj.show_name = show
        return self

    def hide(
        self,
        view: Literal["wireframe", "none"] = "wireframe",  # Preview visibility mode
    ):
        """
        Hide object from render output while controlling preview visibility.
        """
        self.obj.hide_render = True
        # Also disable Cycles visibility channels to ensure the object never
        # contributes to rendered outputs in any pass.
        self.obj.visible_camera = False
        self.obj.visible_diffuse = False
        self.obj.visible_glossy = False
        self.obj.visible_transmission = False
        self.obj.visible_volume_scatter = False
        self.obj.visible_shadow = False

        if view == "wireframe":
            self.obj.hide_set(False)
            self.obj.hide_viewport = False
            self.obj.display_type = "WIRE"
        elif view == "none":
            self.obj.hide_set(True)
            self.obj.hide_viewport = True
        else:
            raise ValueError("view must be one of: wireframe, none.")
        return self

    def get_dimensions(
        self,
        space: Literal["world", "local"] = "world",  # Coordinate space for dimensions
    ) -> Float3:
        """
        Get object dimensions (axis-aligned extents) in world or local space.
        """
        if space == "world":
            dims = self.obj.dimensions
            return (float(dims.x), float(dims.y), float(dims.z))
        if space != "local":
            raise ValueError("space must be one of: world, local.")

        points = _get_object_local_vertices(self.obj)
        if len(points) == 0:
            points = [Vector(corner) for corner in getattr(self.obj, "bound_box", [])]
        if len(points) == 0:
            dims = self.obj.dimensions
            sx, sy, sz = self.obj.scale
            if abs(sx) < 1e-9 or abs(sy) < 1e-9 or abs(sz) < 1e-9:
                return (float(dims.x), float(dims.y), float(dims.z))
            return (float(dims.x / sx), float(dims.y / sy), float(dims.z / sz))

        pmin, pmax = _aabb_from_points(points)
        size = pmax - pmin
        return (float(size.x), float(size.y), float(size.z))

    def inspect(
        self,
        applied_scale: bool = True,  # Include object scale in local dimensions
    ) -> ObjectStats:
        """
        Inspect geometric stats for this object.
        """
        return self.scene.inspect_object(self, applied_scale=applied_scale)

    def get_bounds(
        self,
        space: Literal["world", "local"] = "world",  # Coordinate space for bounds
    ) -> dict[str, Float3]:
        """
        Get axis-aligned bounds in world or local space.
        """
        if space == "world":
            points = _get_object_world_vertices(self.obj)
            if len(points) == 0:
                points = [
                    self.obj.matrix_world @ Vector(corner)
                    for corner in getattr(self.obj, "bound_box", [])
                ]
        elif space == "local":
            points = _get_object_local_vertices(self.obj)
            if len(points) == 0:
                points = [
                    Vector(corner) for corner in getattr(self.obj, "bound_box", [])
                ]
        else:
            raise ValueError("space must be one of: world, local.")

        if len(points) == 0:
            origin = Vector((0.0, 0.0, 0.0))
            return {
                "min": tuple(origin),
                "max": tuple(origin),
                "center": tuple(origin),
                "size": tuple(origin),
            }

        pmin, pmax = _aabb_from_points(points)
        center = (pmin + pmax) * 0.5
        size = pmax - pmin
        return {
            "min": (float(pmin.x), float(pmin.y), float(pmin.z)),
            "max": (float(pmax.x), float(pmax.y), float(pmax.z)),
            "center": (float(center.x), float(center.y), float(center.z)),
            "size": (float(size.x), float(size.y), float(size.z)),
        }

    def add_rigidbody(
        self,
        mode: Literal[
            "box", "sphere", "hull", "mesh", "capsule", "cylinder", "cone"
        ] = "hull",  # Collision shape
        body_type: Literal["ACTIVE", "PASSIVE"] = "ACTIVE",  # Rigid body type
        mass: float = 1.0,  # Body mass
        friction: float = 0.5,  # Surface friction
        restitution: float = 0.0,  # Bounciness
        linear_damping: float = 0.04,  # Linear damping factor
        angular_damping: float = 0.1,  # Angular damping factor
    ) -> "Object":
        """
        Add or update rigid-body settings for this object.
        """
        shape_map = {
            "box": "BOX",
            "sphere": "SPHERE",
            "hull": "CONVEX_HULL",
            "mesh": "MESH",
            "capsule": "CAPSULE",
            "cylinder": "CYLINDER",
            "cone": "CONE",
        }
        if mode not in shape_map:
            raise ValueError(
                "mode must be one of: box, sphere, hull, mesh, capsule, cylinder, cone."
            )
        if self.obj.type != "MESH":
            raise TypeError("Rigid body is supported only for mesh objects.")
        _ensure_rigidbody_world()
        self._select_for_shading_ops()
        if self.obj.rigid_body is None:
            bpy.ops.rigidbody.object_add(type=body_type)

        rb = self.obj.rigid_body
        rb.type = body_type
        rb.collision_shape = shape_map[mode]
        rb.mass = max(float(mass), 1e-6)
        rb.friction = float(friction)
        rb.restitution = float(restitution)
        rb.linear_damping = float(linear_damping)
        rb.angular_damping = float(angular_damping)
        if hasattr(rb, "use_margin"):
            rb.use_margin = True
        if hasattr(rb, "collision_margin"):
            rb.collision_margin = max(0.0, min(self.get_dimensions("world")) * 0.01)
        return self

    def remove_rigidbody(
        self,
        keep_transform: bool = True,  # Preserve world transform after removal
    ) -> "Object":
        """
        Remove rigid body from this object if present.
        """
        if self.obj.rigid_body is None:
            return self

        matrix = self.obj.matrix_world.copy()
        self._select_for_shading_ops()
        bpy.ops.rigidbody.object_remove()
        if keep_transform:
            self.obj.matrix_world = matrix
        return self

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "index": self.index,
                "name": self.obj.name,
                "tags": list(self.tags),
                "properties": self.properties,
                "modifier_parameters": self.modifier_parameters,
                "materials": [
                    slot.material.name
                    for slot in self.obj.material_slots
                    if slot.material is not None
                ],
                "location": tuple(self.obj.location),
                "rotation": tuple(self.obj.rotation_euler),
                "scale": tuple(self.obj.scale),
            }
        )
        return res


class Camera(Object):
    """
    `Object` specialization with camera-specific controls.
    """

    def set_fov(
        self,
        angle: float,  # Camera FOV in degrees
    ):
        """
        Sets the field of view (FOV) for the object's camera in degrees.
        """
        self.obj.data.lens_unit = "FOV"
        self.obj.data.angle = math.radians(angle)
        return self

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "fov_degrees": math.degrees(self.obj.data.angle),
            }
        )
        return res


class Light(Object):
    """
    Base object wrapper for Blender lights with chainable parameter setters.
    """

    _allowed_area_shapes = {"SQUARE", "RECTANGLE", "DISK", "ELLIPSE"}

    def __init__(self, obj: bpy.types.Object, scene: "Scene") -> None:
        if obj.type != "LIGHT":
            raise TypeError("Light wrapper requires an object of type 'LIGHT'.")
        super().__init__(obj, scene, register_object=False)
        self.index = self.scene._register_light(self)
        self.obj.pass_index = self.index

    @property
    def light_data(self) -> bpy.types.Light:
        """
        Return the underlying Blender light datablock.
        """
        return self.obj.data

    def set_color(
        self,
        color: Color,  # RGB/RGBA light color
    ) -> "Light":
        """
        Set light RGB color. Alpha (if provided) is ignored.
        """
        rgb = tuple(color)
        if len(rgb) not in (3, 4):
            raise ValueError("Light color must contain 3 (RGB) or 4 (RGBA) values.")
        self.light_data.color = rgb[:3]
        return self

    def set_power(
        self,
        power: float,  # Light power in Blender energy units
    ) -> "Light":
        """
        Set light power in Blender `energy` units.
        """
        if power < 0:
            raise ValueError("Light power must be non-negative.")
        self.light_data.energy = power
        return self

    def set_cast_shadow(
        self,
        enabled: bool = True,  # Shadow-casting toggle
    ) -> "Light":
        """
        Enable or disable shadow casting.
        """
        self.light_data.use_shadow = enabled
        return self

    def set_specular_factor(
        self,
        factor: float,  # Specular contribution factor
    ) -> "Light":
        """
        Set the light contribution to specular highlights.
        """
        self.light_data.specular_factor = factor
        return self

    def set_softness(
        self,
        value: float,  # Softness parameter
    ) -> "Light":
        """
        Set softness parameter mapped to the current light type.
        """
        if value < 0:
            raise ValueError("Light softness must be non-negative.")
        if self.light_data.type == "SUN":
            self.light_data.angle = value
        else:
            self.light_data.shadow_soft_size = value
        return self

    def set_params(self, **kwargs) -> "Light":
        """
        Set known light-data attributes or custom properties.
        """
        for key, value in kwargs.items():
            if hasattr(self.light_data, key):
                setattr(self.light_data, key, value)
            else:
                self.light_data[key] = value
        return self

    def _type_specific_meta(self) -> dict:
        return {}

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "light_type": self.light_data.type,
                "power": self.light_data.energy,
                "color": tuple(self.light_data.color),
                "cast_shadow": self.light_data.use_shadow,
                "specular_factor": self.light_data.specular_factor,
            }
        )
        res.update(self._type_specific_meta())
        return res


class PointLight(Light):
    """
    Point light with radius control.
    """

    def set_radius(
        self,
        radius: float,  # Radius/soft size
    ) -> "PointLight":
        """
        Set point light radius.
        """
        if radius < 0:
            raise ValueError("Point light radius must be non-negative.")
        self.light_data.shadow_soft_size = radius
        return self

    def _type_specific_meta(self) -> dict:
        return {"radius": self.light_data.shadow_soft_size}


class SunLight(Light):
    """
    Directional sun light with angular size control.
    """

    def set_angle(
        self,
        angle_radians: float,  # Angular sun size in radians
    ) -> "SunLight":
        """
        Set sun angular size in radians.
        """
        if angle_radians < 0:
            raise ValueError("Sun light angle must be non-negative.")
        self.light_data.angle = angle_radians
        return self

    def _type_specific_meta(self) -> dict:
        return {"angle": self.light_data.angle}


class AreaLight(Light):
    """
    Area light with shape and size controls.
    """

    def set_shape(
        self,
        shape: Literal["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"],  # Area-light shape
    ) -> "AreaLight":
        """
        Set area light shape.
        """
        if shape not in self._allowed_area_shapes:
            allowed = ", ".join(sorted(self._allowed_area_shapes))
            raise ValueError(
                f"Unknown area light shape '{shape}'. Allowed: [{allowed}]"
            )
        self.light_data.shape = shape
        return self

    def set_size(
        self,
        size: float,  # Primary size
    ) -> "AreaLight":
        """
        Set primary area light size.
        """
        if size < 0:
            raise ValueError("Area light size must be non-negative.")
        self.light_data.size = size
        return self

    def set_size_xy(
        self,
        size_x: float,  # Size along X
        size_y: float,  # Size along Y
    ) -> "AreaLight":
        """
        Set area light X and Y sizes.
        """
        if size_x < 0 or size_y < 0:
            raise ValueError("Area light sizes must be non-negative.")
        self.light_data.size = size_x
        self.light_data.size_y = size_y
        return self

    def _type_specific_meta(self) -> dict:
        res = {
            "shape": self.light_data.shape,
            "size": self.light_data.size,
        }
        if hasattr(self.light_data, "size_y"):
            res["size_y"] = self.light_data.size_y
        return res


class SpotLight(Light):
    """
    Spot light with cone and blend controls.
    """

    def set_spot_size(
        self,
        angle_radians: float,  # Cone angle in radians
    ) -> "SpotLight":
        """
        Set spotlight cone angle in radians.
        """
        if angle_radians < 0:
            raise ValueError("Spot light angle must be non-negative.")
        self.light_data.spot_size = angle_radians
        return self

    def set_blend(
        self,
        blend: float,  # Edge softness in [0, 1]
    ) -> "SpotLight":
        """
        Set spotlight edge softness in the [0, 1] range.
        """
        if blend < 0 or blend > 1:
            raise ValueError("Spot light blend must be in the [0, 1] range.")
        self.light_data.spot_blend = blend
        return self

    def set_show_cone(
        self,
        show: bool = True,  # Viewport cone visibility
    ) -> "SpotLight":
        """
        Show or hide the spotlight cone in viewport.
        """
        self.light_data.show_cone = show
        return self

    def _type_specific_meta(self) -> dict:
        return {
            "spot_size": self.light_data.spot_size,
            "spot_blend": self.light_data.spot_blend,
            "show_cone": self.light_data.show_cone,
        }


class World(ABC):
    """
    Base class representing world (environment ligthing).
    """

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def _post_gen(self):
        pass

    @abstractmethod
    def set_params(self):
        """
        Update world-specific lighting parameters.
        """
        pass


class BasicWorld(World):
    """
    `World` class representing a single color environmental lighting.
    """

    color: ColorRGBA | None = None  # Environment RGBA color
    strength: float = None  # Background light intensity

    def __init__(self):
        pass

    def _post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True

        # Get the node tree
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Create nodes
        node_background = nodes.new(type="ShaderNodeBackground")
        node_output = nodes.new(type="ShaderNodeOutputWorld")

        node_background.location = (0, 0)
        node_output.location = (200, 0)

        # Connect nodes
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.color is not None:
            node_background.inputs["Color"].default_value = self.color
        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength

    def set_params(
        self,
        color: ColorRGBA | None = None,  # environement color
        strength: float = None,  # envronement light strength
    ):
        """
        Set ligthing parameters.
        """
        if color is not None:
            self.color = color
        if strength is not None:
            self.strength = strength


class SkyWorld(World):
    """
    `World` class representing a procedural sky environement.

    For more information, view [official blender docs](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/sky.html).
    """

    strength: float = None  # Background light intensity

    sun_size: float = None  # Sun angular size
    sun_intensity: float = None  # Sun intensity

    sun_elevation: float = None  # Sun elevation angle
    rotation_z: float = None  # Sun azimuth rotation

    altitude: float = None  # Observer altitude

    air: float = 0.1  # Air density
    aerosol_density: float = 0.01  # Aerosol density
    ozone: float = 10.0  # Ozone density

    def __init__(self):
        pass

    def _post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True

        # Get the node tree
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Create nodes
        node_background = nodes.new(type="ShaderNodeBackground")
        node_sky_tex = nodes.new(type="ShaderNodeTexSky")
        node_output = nodes.new(type="ShaderNodeOutputWorld")

        node_sky_tex.location = (-300, 0)
        node_background.location = (0, 0)
        node_output.location = (200, 0)

        # Connect nodes
        links.new(node_sky_tex.outputs["Color"], node_background.inputs["Color"])
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength

        if self.sun_size is not None:
            node_sky_tex.sun_size = self.sun_size
        if self.sun_intensity is not None:
            node_sky_tex.sun_intensity = self.sun_intensity

        if self.sun_elevation is not None:
            node_sky_tex.sun_elevation = self.sun_elevation
        if self.rotation_z is not None:
            node_sky_tex.sun_rotation = self.rotation_z

        if self.altitude is not None:
            node_sky_tex.altitude = self.altitude

        if self.air is not None:
            node_sky_tex.air_density = self.air
        if self.aerosol_density is not None:
            node_sky_tex.aerosol_density = self.aerosol_density
        if self.ozone is not None:
            node_sky_tex.ozone_density = self.ozone

    def set_params(
        self,
        strength: float = None,  # Environement light strength
        sun_size: float = None,  # Sun angular size
        sun_intensity: float = None,  # Sun intensity
        sun_elevation: float = None,  # Sun elevation
        rotation_z: float = None,  # Angle representing the sun direction
        air: float = None,  # Air density
        aerosol_density: float = None,  # Aerosol density
        ozone: float = None,  # Ozone density
    ):
        """
        Set procedural sky parameters for the current world.
        """
        if strength is not None:
            self.strength = strength
        if sun_size is not None:
            self.sun_size = sun_size
        if sun_intensity is not None:
            self.sun_intensity = sun_intensity
        if sun_elevation is not None:
            self.sun_elevation = sun_elevation
        if rotation_z is not None:
            self.rotation_z = rotation_z
        if air is not None:
            self.air = air
        if aerosol_density is not None:
            self.aerosol_density = aerosol_density
        if ozone is not None:
            self.ozone = ozone


class HDRIWorld(World):
    """
    `World` class for importing lighting from an hdri `.exr` file.

    HDRI files can be captured by a 360 camera or a smartphone app or downloaded from public libraries such as [polyhaven](https://polyhaven.com/hdris).
    """

    hdri_path: str  # Path to HDRI image file
    strength: float = None  # Environment light intensity multiplier
    rotation_z: float = None  # Rotation around world Z axis

    def __init__(self, hdri_path: str):
        self.hdri_path = hdri_path

    def _post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True

        # Get the node tree
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Clear existing nodes
        nodes.clear()

        # Create nodes
        node_background = nodes.new(type="ShaderNodeBackground")
        node_env_tex = nodes.new(type="ShaderNodeTexEnvironment")
        node_output = nodes.new(type="ShaderNodeOutputWorld")
        node_mapping = nodes.new(type="ShaderNodeMapping")
        node_coord = nodes.new(type="ShaderNodeTexCoord")

        node_coord.location = (-700, 0)
        node_mapping.location = (-500, 0)
        node_env_tex.location = (-300, 0)
        node_background.location = (0, 0)
        node_output.location = (200, 0)

        # Connect nodes
        links.new(node_coord.outputs["Generated"], node_mapping.inputs["Vector"])
        links.new(node_mapping.outputs["Vector"], node_env_tex.inputs["Vector"])
        links.new(node_env_tex.outputs["Color"], node_background.inputs["Color"])
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.hdri_path is not None:
            node_env_tex.image = bpy.data.images.load(
                self.hdri_path, check_existing=False
            )
            _mark_owned(node_env_tex.image)

        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength

        if self.rotation_z is not None:
            node_mapping.inputs["Rotation"].default_value[2] = self.rotation_z

    def set_params(
        self,
        hdri_path: str = None,  # Path to the `.exr` file
        strength: float = None,  # Environment intensity multiplier
        rotation_z: float = None,  # Rotation around world Z axis
    ):
        """
        Set HDRI source and environment lighting parameters.
        """
        if hdri_path is not None:
            self.hdri_path = hdri_path
        if strength is not None:
            self.strength = strength
        if rotation_z is not None:
            self.rotation_z = rotation_z


class ImportedWorld(World):
    """
    `World` class for importing environment lighting from a `.blend` file.

    Use it to bring in custom procedural lighting setups and adjust their parameters by the script.
    """

    filepath: str  # Source .blend file path
    world_name: str = None  # World name inside source .blend
    params: dict  # Custom properties applied to imported world

    def __init__(self, filepath: str, world_name: str = None):
        self.filepath = filepath
        self.world_name = world_name
        self.params = dict()

    def _post_gen(self):
        with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
            if self.world_name is None:
                data_to.worlds = [data_from.worlds[0]]
            else:
                data_to.worlds = [self.world_name]
        imported_world = data_to.worlds[0]
        _mark_world_tree(imported_world)
        bpy.context.scene.world = imported_world

        for k, v in self.params.items():
            bpy.context.scene.world[k] = v

    def set_params(self, **kwargs):
        """
        Set custom properties applied to the imported world.
        """
        self.params.update(kwargs)


def _use_cycles() -> None:
    if bpy.context.scene.render.engine != "CYCLES":
        bpy.context.scene.render.engine = "CYCLES"


def _use_gpu():
    if bpy.context.scene.cycles.device != "GPU":
        bpy.context.scene.cycles.device = "GPU"


def _deselect():
    bpy.ops.object.select_all(action="DESELECT")


def _set_resolution(resolution: Resolution):
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100


def _set_time_limit(time_limit: float):
    bpy.context.scene.cycles.time_limit = time_limit


def _configure_passes(
    passes: RenderPassSet, semantic_channels: SemanticChannelSet | None = None
):
    """
    Enable/disable Cycles render-passes according to the `passes` list.
    """
    layer = bpy.context.view_layer

    # Disable every pass first to get a clean slate
    for attr in PASS_MAP.values():
        if hasattr(layer, attr):
            setattr(layer, attr, False)

    # Turn on requested passes
    for p in passes:
        attr = PASS_MAP.get(p)
        if attr and hasattr(layer, attr):
            setattr(layer, attr, True)
        else:
            print(f"[rv] Warning: unknown or unsupported pass '{p.name}' – skipped.")

    # We always need Object-Index for segmentation masks
    layer.use_pass_object_index = True

    _configure_semantic_aovs(layer, semantic_channels or set())


def _configure_semantic_aovs(layer, semantic_channels: SemanticChannelSet) -> None:
    if not hasattr(layer, "aovs"):
        return

    for aov in list(layer.aovs):
        aov_name = getattr(aov, "name", "")
        if _normalize_socket_name(aov_name) in semantic_channels:
            layer.aovs.remove(aov)

    for channel in sorted(semantic_channels):
        aov = layer.aovs.add()
        aov.name = _semantic_aov_name(channel)
        if hasattr(aov, "type"):
            aov.type = "VALUE"


def _configure_compositor(
    output_dir: str,  # Directory where rendered output files will be saved
    semantic_channels: SemanticChannelSet | None = None,
    semantic_mask_threshold: float = 0.5,
) -> None:
    """
    Configure compositor nodes in Blender 5 for saving render outputs.
    """
    scene = bpy.context.scene
    tree = _get_compositor_tree(scene)
    tree.nodes.clear()
    tree.links.clear()

    dx, dy = 350, 60

    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers.location = (0, 0)

    _connect_group_output_image(tree, render_layers, dx, dy)

    file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    file_out_node.location = (2 * dx, 0)
    _reset_file_output_node(file_out_node, output_dir)
    _configure_file_output_node_format(
        file_out_node,
        file_format="PNG",
        color_mode="RGBA",
        color_depth="8",
    )

    index_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    index_file_out_node.location = (2 * dx + 40, -350)
    _reset_file_output_node(index_file_out_node, output_dir)
    _configure_file_output_node_format(
        index_file_out_node,
        file_format="PNG",
        color_mode="RGB",
        color_depth="16",
    )

    semantic_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    semantic_file_out_node.location = (2 * dx + 80, -700)
    _reset_file_output_node(semantic_file_out_node, output_dir)
    _configure_file_output_node_format(
        semantic_file_out_node,
        file_format="PNG",
        color_mode="BW",
        color_depth="16",
    )

    depth_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    depth_file_out_node.location = (2 * dx + 120, -1050)
    _reset_file_output_node(depth_file_out_node, output_dir)
    _configure_file_output_node_format(
        depth_file_out_node,
        file_format="OPEN_EXR",
        color_mode="BW",
        color_depth="32",
    )

    depth_preview_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    depth_preview_file_out_node.location = (2 * dx + 160, -1250)
    _reset_file_output_node(depth_preview_file_out_node, output_dir)
    _configure_file_output_node_format(
        depth_preview_file_out_node,
        file_format="PNG",
        color_mode="BW",
        color_depth="16",
    )

    index_ob = _find_socket_by_name(render_layers.outputs, "Object Index")
    index_ma = _find_socket_by_name(render_layers.outputs, "Material Index")
    index_sockets = [index_ob, index_ma]

    semantic_outputs: dict[str, typing.Any] = {}
    semantic_names = {
        _normalize_socket_name(_semantic_aov_name(channel))
        for channel in (semantic_channels or set())
    }
    depth_preview_connected = False

    for output in render_layers.outputs:
        if output in index_sockets:
            continue

        normalized_name = _normalize_socket_name(output.name)
        if normalized_name in semantic_names:
            semantic_outputs[output.name] = output
            continue

        # Store raw depth in float EXR to avoid clamping (PNG clips values > 1.0).
        if normalized_name in {"depth", "z"}:
            depth_slot_name = output.name
            depth_input = _add_file_output_item(
                depth_file_out_node, depth_slot_name, output
            )
            _configure_file_output_item(
                depth_file_out_node,
                depth_slot_name,
                file_path=depth_slot_name,
            )
            tree.links.new(output, depth_input)

            if not depth_preview_connected:
                normalize_node = tree.nodes.new(type="CompositorNodeNormalize")
                normalize_node.location = (dx, -1200)
                normalize_node.hide = True
                tree.links.new(output, normalize_node.inputs[0])

                preview_slot_name = "DepthPreview"
                preview_input = _add_file_output_item(
                    depth_preview_file_out_node,
                    preview_slot_name,
                    normalize_node.outputs[0],
                )
                _configure_file_output_item(
                    depth_preview_file_out_node,
                    preview_slot_name,
                    file_path=preview_slot_name,
                )
                tree.links.new(normalize_node.outputs[0], preview_input)
                depth_preview_connected = True
            continue

        slot_name = output.name
        out_input = _add_file_output_item(file_out_node, slot_name, output)
        _configure_file_output_item(
            file_out_node,
            slot_name,
            file_path=slot_name,
        )
        tree.links.new(output, out_input)

    preview_group = bpy.data.node_groups.get("PreviewIndex")
    for i, index_output in enumerate(index_sockets):
        if index_output is None:
            continue

        divider_node = tree.nodes.new(type="ShaderNodeMath")
        divider_node.operation = "DIVIDE"
        divider_node.inputs[1].default_value = 2**16
        divider_node.location = (dx, -350 - dy * i)
        divider_node.hide = True

        index_name = _index_slot_name(i)
        index_input = _add_file_output_item(
            index_file_out_node, index_name, index_output
        )
        _configure_file_output_item(
            index_file_out_node,
            index_name,
            file_path=index_name,
        )
        tree.links.new(index_output, divider_node.inputs[0])
        tree.links.new(divider_node.outputs[0], index_input)

        if preview_group is not None:
            preview_node = tree.nodes.new(type="CompositorNodeGroup")
            preview_node.node_tree = preview_group
            preview_node.location = (dx, -200 - dy * i)
            preview_node.label = f"{index_name} Preview"
            preview_node.hide = True

            preview_input = _find_socket_by_name(preview_node.inputs, "Index")
            preview_output = _find_socket_by_name(preview_node.outputs, "Preview")
            if preview_input is not None and preview_output is not None:
                preview_name = _preview_slot_name(i)
                preview_file_input = _add_file_output_item(
                    file_out_node, preview_name, preview_output
                )
                _configure_file_output_item(
                    file_out_node,
                    preview_name,
                    file_path=preview_name,
                )
                tree.links.new(index_output, preview_input)
                tree.links.new(preview_output, preview_file_input)

    for socket_name, socket in semantic_outputs.items():
        threshold = tree.nodes.new(type="ShaderNodeMath")
        threshold.operation = "GREATER_THAN"
        threshold.inputs[1].default_value = semantic_mask_threshold
        threshold.location = (dx, -700 - dy)
        threshold.hide = True
        tree.links.new(socket, threshold.inputs[0])

        channel = _normalize_semantic_channel(socket_name)
        mask_slot_name = f"Mask_{channel}"
        sem_input = _add_file_output_item(
            semantic_file_out_node,
            mask_slot_name,
            threshold.outputs[0],
        )
        _configure_file_output_item(
            semantic_file_out_node,
            mask_slot_name,
            file_path=mask_slot_name,
        )
        tree.links.new(threshold.outputs[0], sem_input)


def _get_compositor_tree(scene: bpy.types.Scene):
    tree = scene.compositing_node_group
    if tree is None:
        tree = bpy.data.node_groups.new(
            name=f"RVCompositor_{scene.name}",
            type="CompositorNodeTree",
        )
        _mark_node_tree(tree)
        scene.compositing_node_group = tree
    else:
        _mark_node_tree(tree)
    return tree


def _connect_group_output_image(tree, render_layers, dx: float, dy: float):
    group_output = tree.nodes.new(type="NodeGroupOutput")
    group_output.location = (dx, dy)

    _ensure_group_output_socket(tree, "Image")
    image_input = _find_socket_by_name(group_output.inputs, "Image")
    image_output = _find_socket_by_name(render_layers.outputs, "Image")
    if image_input is None or image_output is None:
        raise RuntimeError("Failed to bind compositor Image output socket.")
    tree.links.new(image_output, image_input)


def _ensure_group_output_socket(tree, socket_name: str):
    target = _normalize_socket_name(socket_name)
    for item in tree.interface.items_tree:
        item_name = getattr(item, "name", None)
        if item_name is not None and _normalize_socket_name(item_name) == target:
            return

    tree.interface.new_socket(
        name=socket_name,
        in_out="OUTPUT",
        socket_type="NodeSocketColor",
    )


def _reset_file_output_node(node, output_dir: str | None):
    node.file_output_items.clear()
    if output_dir is not None:
        node.directory = output_dir
    node.file_name = ""


def _add_file_output_item(node, slot_name: str, source_socket):
    node.file_output_items.new(_socket_type_for_output_item(source_socket), slot_name)
    output_input = _find_socket_by_name(node.inputs, slot_name)
    if output_input is None:
        raise RuntimeError(f"File output socket '{slot_name}' was not created.")
    return output_input


def _configure_file_output_item(
    node,
    slot_name: str,
    file_path: str,
):
    item = _find_file_output_item(node, slot_name)
    if item is None:
        raise RuntimeError(f"File output item '{slot_name}' not found.")

    if hasattr(item, "override_node_format"):
        item.override_node_format = False
    if hasattr(item, "path"):
        item.path = file_path
    if hasattr(item, "name"):
        item.name = file_path


def _configure_file_output_node_format(
    node,
    file_format: str,
    color_mode: str,
    color_depth: str,
):
    if hasattr(node.format, "media_type"):
        node.format.media_type = "IMAGE"
    node.format.file_format = file_format
    node.format.color_mode = color_mode
    node.format.color_depth = color_depth


def _find_file_output_item(node, slot_name: str):
    target = _normalize_socket_name(slot_name)
    for item in node.file_output_items:
        if _normalize_socket_name(item.name) == target:
            return item
    return None


def _socket_type_for_output_item(source_socket) -> str:
    socket_type = str(getattr(source_socket, "type", "RGBA")).upper()
    mapping = {
        "VALUE": "FLOAT",
        "COLOR": "RGBA",
    }
    socket_type = mapping.get(socket_type, socket_type)

    valid = {
        "FLOAT",
        "INT",
        "BOOLEAN",
        "VECTOR",
        "RGBA",
        "ROTATION",
        "MATRIX",
        "STRING",
        "MENU",
        "SHADER",
        "OBJECT",
        "IMAGE",
        "GEOMETRY",
        "COLLECTION",
        "TEXTURE",
        "MATERIAL",
        "BUNDLE",
        "CLOSURE",
    }
    if socket_type not in valid:
        return "RGBA"
    return socket_type


def _index_slot_name(idx: int) -> str:
    return "IndexOB" if idx == 0 else "IndexMA"


def _preview_slot_name(idx: int) -> str:
    return "PreviewIndexOB" if idx == 0 else "PreviewIndexMA"


def _normalize_socket_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_socket_by_name(sockets, candidate: str):
    if candidate in sockets:
        return sockets[candidate]

    target = _normalize_socket_name(candidate)
    for socket in sockets:
        if _normalize_socket_name(socket.name) == target:
            return socket
    return None


def _ensure_positive_tuple(values, expected_len: int, name: str) -> None:
    if len(values) != expected_len:
        raise ValueError(f"{name} must contain exactly {expected_len} values.")
    for value in values:
        if float(value) <= 0:
            raise ValueError(f"{name} values must be > 0.")


def _validate_scatter_common(
    source: ObjectLoaderSource,
    count: int,
    domain: "Domain",
    min_gap: float,
    yaw_range: Float2,
    rotation_mode: str,
    scale_range: Float2,
    max_attempts_per_object: int,
    boundary_mode: str,
    boundary_margin: float,
) -> ScatterValidationResult:
    if count <= 0:
        raise ValueError("count must be > 0.")
    if not isinstance(domain, Domain):
        raise TypeError("domain must be an instance of Domain.")
    if min_gap < 0:
        raise ValueError("min_gap must be >= 0.")
    if boundary_margin < 0:
        raise ValueError("boundary_margin must be >= 0.")
    if max_attempts_per_object <= 0:
        raise ValueError("max_attempts_per_object must be > 0.")
    if boundary_mode != "center_margin":
        raise ValueError("boundary_mode must be center_margin.")
    if rotation_mode not in {"yaw", "free"}:
        raise ValueError("rotation_mode must be one of: yaw, free.")
    if len(scale_range) != 2:
        raise ValueError("scale_range must contain exactly two values.")
    scale_min = float(scale_range[0])
    scale_max = float(scale_range[1])
    if scale_min <= 0 or scale_max <= 0:
        raise ValueError("scale_range values must be > 0.")
    if scale_min > scale_max:
        raise ValueError("scale_range must satisfy min <= max.")
    if len(yaw_range) != 2:
        raise ValueError("yaw_range must contain exactly two values.")
    yaw_min = float(yaw_range[0])
    yaw_max = float(yaw_range[1])
    if yaw_min > yaw_max:
        raise ValueError("yaw_range must satisfy min <= max.")

    loaders: list[ObjectLoader]
    if isinstance(source, ObjectLoader):
        loaders = [source]
    elif isinstance(source, (list, tuple)) and len(source) > 0:
        if not all(isinstance(loader, ObjectLoader) for loader in source):
            raise TypeError("source sequence must contain only ObjectLoader instances.")
        loaders = list(source)
    else:
        raise TypeError(
            "source must be ObjectLoader or non-empty sequence[ObjectLoader]."
        )

    for loader in loaders:
        if getattr(loader.obj, "data", None) is None:
            raise ValueError("source object must have geometry data.")

    return loaders, scale_min, scale_max, yaw_min, yaw_max


def _init_scatter_stats(
    requested: int, domain_kind: str, strategy: str, seed: int | None
) -> dict:
    return {
        "requested": requested,
        "placed": 0,
        "attempts": 0,
        "rejected_boundary": 0,
        "rejected_overlap": 0,
        "rejected_attempt_limit": 0,
        "strategy": strategy,
        "domain_kind": domain_kind,
        "seed": seed,
    }


def _finalize_scatter_stats(
    scene: Scene, stats: dict, placed: list["Object"], requested: int
) -> None:
    stats["placed"] = len(placed)
    if len(placed) < requested:
        warnings.warn(
            "scatter placed "
            f"{len(placed)}/{requested} objects after {stats['attempts']} attempts "
            f"(strategy={stats['strategy']}, domain={stats['domain_kind']}, seed={stats['seed']})."
        )

    scatter_runs = scene.custom_meta.get("scatter_runs", [])
    if not isinstance(scatter_runs, list):
        scatter_runs = [scatter_runs]
    scatter_runs.append(stats)
    scene.custom_meta["scatter_runs"] = scatter_runs


def _overlaps_by_radius(
    position: Vector,
    radius: float,
    neighbors: list[int],
    placed_infos: list[dict],
    dimension: int,
    min_gap: float,
) -> bool:
    for neighbor_idx in neighbors:
        neighbor = placed_infos[neighbor_idx]
        if dimension == 2:
            dist = math.hypot(
                position.x - neighbor["position"].x,
                position.y - neighbor["position"].y,
            )
        else:
            dist = (position - neighbor["position"]).length
        if dist + 1e-9 < radius + neighbor["radius"] + min_gap:
            return True
    return False


def _remove_blender_object(obj: bpy.types.Object) -> None:
    if obj is None:
        return
    try:
        bpy.data.objects.remove(obj, do_unlink=True)
    except Exception:
        pass


def _ensure_rigidbody_world() -> None:
    scene = bpy.context.scene
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()


def _configure_rigidbody_world(
    settle_frames: int, substeps: int, time_scale: float
) -> tuple[int, int]:
    _ensure_rigidbody_world()
    scene = bpy.context.scene
    rbw = scene.rigidbody_world
    if rbw is None:
        raise RuntimeError("Failed to initialize rigid body world.")

    start_frame = int(scene.frame_start)
    frame_count = max(1, int(settle_frames))
    end_frame = start_frame + frame_count - 1
    scene.frame_set(start_frame)
    if hasattr(scene, "sync_mode"):
        scene.sync_mode = "NONE"
    if hasattr(rbw, "time_scale"):
        rbw.time_scale = float(time_scale)
    if hasattr(rbw, "substeps_per_frame"):
        rbw.substeps_per_frame = max(1, int(substeps))
    if hasattr(rbw, "solver_iterations"):
        rbw.solver_iterations = max(1, int(substeps) * 2)

    cache = getattr(rbw, "point_cache", None)
    if cache is not None:
        cache.frame_start = start_frame
        cache.frame_end = end_frame
    return start_frame, end_frame


def _simulate_rigidbody(
    settle_frames: int, substeps: int, time_scale: float
) -> tuple[int, int]:
    start_frame, end_frame = _configure_rigidbody_world(
        settle_frames=settle_frames, substeps=substeps, time_scale=time_scale
    )
    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
    return start_frame, end_frame


def simulate_physics(
    frames: int = 20,  # Number of simulation frames
    substeps: int = 10,  # Substeps per frame
    time_scale: float = 1.0,  # Physics time scale
) -> None:
    """
    Simulate current Blender rigid-body world for a fixed number of frames.

    Users are expected to explicitly add rigid bodies via `Object.add_rigidbody(...)`
    and then call `rv.simulate_physics(...)` at chosen points in scene generation.
    """
    if frames <= 0:
        raise ValueError("frames must be > 0.")
    if substeps <= 0:
        raise ValueError("substeps must be > 0.")
    if time_scale <= 0:
        raise ValueError("time_scale must be > 0.")

    _simulate_rigidbody(
        settle_frames=int(frames), substeps=int(substeps), time_scale=float(time_scale)
    )


def _estimate_loader_radius(loader: "ObjectLoader", dimension: int) -> float:
    temp = loader.create_instance(register_object=False)
    try:
        return _object_world_radius(temp.obj, dimension)
    finally:
        _remove_blender_object(temp.obj)


def _cross_2d(o, a, b) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _convex_hull_2d(points: Polygon2D) -> Polygon2D:
    pts = sorted(set((float(p[0]), float(p[1])) for p in points))
    if len(pts) <= 1:
        return pts
    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross_2d(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross_2d(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _polygon_signed_area(points: Polygon2D) -> float:
    area = 0.0
    for i in range(len(points)):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return area * 0.5


def _sample_convex_polygon(points: Polygon2D, rng: random.Random) -> Float2:
    p0 = points[0]
    tris = []
    total_area = 0.0
    for i in range(1, len(points) - 1):
        p1 = points[i]
        p2 = points[i + 1]
        area = abs(_cross_2d(p0, p1, p2))
        if area > 1e-12:
            tris.append((p0, p1, p2, area))
            total_area += area
    if total_area <= 0:
        raise ValueError("polygon is degenerate.")

    choice = rng.uniform(0.0, total_area)
    accum = 0.0
    selected = tris[-1]
    for tri in tris:
        accum += tri[3]
        if choice <= accum:
            selected = tri
            break

    a, b, c, _ = selected
    r1 = math.sqrt(rng.random())
    r2 = rng.random()
    ax, ay = a
    bx, by = b
    cx, cy = c
    x = (1 - r1) * ax + r1 * ((1 - r2) * bx + r2 * cx)
    y = (1 - r1) * ay + r1 * ((1 - r2) * by + r2 * cy)
    return (x, y)


def _point_in_convex_polygon(point: Float2, points) -> bool:
    sign = 0
    for i in range(len(points)):
        a = points[i]
        b = points[(i + 1) % len(points)]
        cross = _cross_2d(a, b, point)
        if abs(cross) <= 1e-10:
            continue
        current_sign = 1 if cross > 0 else -1
        if sign == 0:
            sign = current_sign
        elif sign != current_sign:
            return False
    return True


def _distance_point_segment_2d(point, a, b) -> float:
    px, py = point
    ax, ay = a
    bx, by = b
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    denom = abx * abx + aby * aby
    if denom <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / denom))
    cx = ax + t * abx
    cy = ay + t * aby
    return math.hypot(px - cx, py - cy)


def _distance_to_polygon_edges(point: Float2, points) -> float:
    best = float("inf")
    for i in range(len(points)):
        best = min(
            best,
            _distance_point_segment_2d(point, points[i], points[(i + 1) % len(points)]),
        )
    return best


def _random_unit_vector(rng: random.Random) -> Vector:
    z = rng.uniform(-1.0, 1.0)
    theta = rng.uniform(0.0, 2.0 * math.pi)
    t = math.sqrt(max(0.0, 1.0 - z * z))
    return Vector((t * math.cos(theta), t * math.sin(theta), z))


def _points_centroid(points: list[Vector]) -> Vector:
    if len(points) == 0:
        return Vector((0.0, 0.0, 0.0))
    total = Vector((0.0, 0.0, 0.0))
    for p in points:
        total += p
    return total / len(points)


def _aabb_from_points(points: list[Vector]) -> AABB:
    xs = [p.x for p in points]
    ys = [p.y for p in points]
    zs = [p.z for p in points]
    return Vector((min(xs), min(ys), min(zs))), Vector((max(xs), max(ys), max(zs)))


def _get_object_world_vertices(obj: bpy.types.Object) -> list[Vector]:
    if obj is None:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return []
    mesh = obj_eval.to_mesh()
    try:
        return [obj_eval.matrix_world @ v.co for v in mesh.vertices]
    finally:
        obj_eval.to_mesh_clear()


def _get_object_local_vertices(obj: bpy.types.Object) -> list[Vector]:
    if obj is None:
        return []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return []
    mesh = obj_eval.to_mesh()
    try:
        return [Vector(v.co) for v in mesh.vertices]
    finally:
        obj_eval.to_mesh_clear()


def _convex_hull_planes(points: list[Vector]) -> list[Float4]:
    bm = bmesh.new()
    for p in points:
        bm.verts.new(p)
    bm.verts.ensure_lookup_table()
    if len(bm.verts) < 4:
        bm.free()
        return []

    hull = bmesh.ops.convex_hull(bm, input=list(bm.verts))
    if len(hull.get("geom", [])) == 0:
        bm.free()
        return []

    bm.normal_update()
    centroid = _points_centroid(points)
    planes = []
    for face in bm.faces:
        n = Vector(face.normal)
        p = Vector(face.verts[0].co)
        d = -n.dot(p)
        if n.dot(centroid) + d > 0:
            n = -n
            d = -d
        planes.append((n.x, n.y, n.z, d))
    bm.free()
    return planes


def _sample_rotation_quaternion(
    rng: random.Random,
    domain_dimension: int,
    rotation_mode: str,
    yaw_min: float,
    yaw_max: float,
) -> mathutils.Quaternion:
    if rotation_mode == "yaw" or domain_dimension == 2:
        yaw_deg = rng.uniform(yaw_min, yaw_max)
        return mathutils.Euler((0.0, 0.0, math.radians(yaw_deg))).to_quaternion()

    u1, u2, u3 = rng.random(), rng.random(), rng.random()
    qx = math.sqrt(1.0 - u1) * math.sin(2.0 * math.pi * u2)
    qy = math.sqrt(1.0 - u1) * math.cos(2.0 * math.pi * u2)
    qz = math.sqrt(u1) * math.sin(2.0 * math.pi * u3)
    qw = math.sqrt(u1) * math.cos(2.0 * math.pi * u3)
    return mathutils.Quaternion((qw, qx, qy, qz))


def _object_world_radius(obj: bpy.types.Object, dimension: int) -> float:
    if obj is None:
        return 0.0

    points = _get_object_world_vertices(obj)
    if len(points) == 0:
        corners = []
        for corner in getattr(obj, "bound_box", []):
            corners.append(obj.matrix_world @ Vector(corner))
        points = corners
    if len(points) == 0:
        dims = getattr(obj, "dimensions", Vector((1.0, 1.0, 1.0)))
        if dimension == 2:
            return 0.5 * math.hypot(dims.x, dims.y)
        return 0.5 * math.sqrt(dims.x * dims.x + dims.y * dims.y + dims.z * dims.z)

    center = obj.matrix_world.translation
    if dimension == 2:
        return max(math.hypot(p.x - center.x, p.y - center.y) for p in points)
    return max((p - center).length for p in points)


def _build_bvh_from_object(
    obj: bpy.types.Object,
    transform: mathutils.Matrix | None = None,
) -> BVHTree | None:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    if obj_eval.type != "MESH":
        return None
    mesh = obj_eval.to_mesh()
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh)
        if transform is None:
            transform = obj_eval.matrix_world.copy()
        bmesh.ops.transform(bm, matrix=transform, verts=bm.verts)
        if len(bm.faces) == 0:
            return None
        return BVHTree.FromBMesh(bm, epsilon=0.0)
    finally:
        bm.free()
        obj_eval.to_mesh_clear()


def _mesh_overlaps_any(
    source_obj: bpy.types.Object,
    location: Vector,
    rotation: mathutils.Quaternion,
    scale: float,
    others: list[bpy.types.Object],
) -> bool:
    transform = (
        mathutils.Matrix.Translation(location)
        @ rotation.to_matrix().to_4x4()
        @ mathutils.Matrix.Diagonal((scale, scale, scale, 1.0))
    )
    candidate_bvh = _build_bvh_from_object(source_obj, transform=transform)
    if candidate_bvh is None:
        return False
    for other in others:
        other_bvh = _build_bvh_from_object(other)
        if other_bvh is None:
            continue
        if len(candidate_bvh.overlap(other_bvh)) > 0:
            return True
    return False


def _mesh_object_overlaps_any(
    candidate: bpy.types.Object, others: list[bpy.types.Object]
) -> bool:
    candidate_bvh = _build_bvh_from_object(candidate)
    if candidate_bvh is None:
        return False
    for other in others:
        other_bvh = _build_bvh_from_object(other)
        if other_bvh is None:
            continue
        if len(candidate_bvh.overlap(other_bvh)) > 0:
            return True
    return False


def _load_single_object(path: str):
    with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects][:1]

    if len(data_to.objects) == 0:
        raise ValueError(f"No objects found in '{path}'.")

    return data_to.objects[0]


def _load_all_objects(path: str):
    with bpy.data.libraries.load(path, link=False) as (data_from, data_to):
        data_to.objects = [name for name in data_from.objects]

    return data_to.objects


def _read_json_property(id_data, key: str):
    raw = id_data.get(key)
    if raw is None or not isinstance(raw, str):
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


def _restore_rv_export_object_metadata(obj: bpy.types.Object) -> dict:
    meta = _read_json_property(obj, "rv_object_json")
    if isinstance(meta, dict):
        return meta

    tags = _read_json_property(obj, "rv_tags_json")
    if tags is None:
        return {}
    return {"tags": tags}


def _restore_modifier_parameters(raw) -> list[dict[str, JSONSerializable]]:
    if not isinstance(raw, list):
        return []

    restored: list[dict[str, JSONSerializable]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        modifier_name = item.get("modifier_name")
        parameter_name = item.get("parameter_name")
        if not isinstance(modifier_name, str) or not isinstance(parameter_name, str):
            continue
        restored.append(
            {
                "modifier_name": modifier_name,
                "parameter_name": parameter_name,
                "value": item.get("value"),
            }
        )
    return restored


def _combine_arglist_set(args):
    result = set()
    for p in args:
        if isinstance(p, (list, tuple, set, frozenset)):
            result = result.union(set(p))
        else:
            result.add(p)
    return result


def _clear_scene():
    # Backward-compatible entrypoint used by older scripts.
    begin_run(purge_orphans=True)
