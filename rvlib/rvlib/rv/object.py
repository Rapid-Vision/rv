from dataclasses import dataclass
import math
import numbers
from typing import TYPE_CHECKING, Any, Literal, Self, Sequence, Union, cast

import bpy
import mathutils
from mathutils import Vector

from .assets import (
    _combine_arglist_set,
    _restore_modifier_parameters,
    _restore_rv_export_object_metadata,
)
from .geometry import (
    _aabb_from_points,
    _get_object_local_vertices,
    _get_object_world_location,
    _get_object_world_vertices,
)
from .modifiers import _resolve_modifier_input_key, _resolve_nodes_modifier
from .physics import _ensure_rigidbody_world
from .types import Color, Float3, JSONSerializable, TagSet
from .utils import (
    _get_generated_collection,
    _mark_material_tree,
    _mark_node_tree,
    _mark_object_tree,
    _require_blender_attr,
)

if TYPE_CHECKING:
    from .material import Material
    from .scene import Scene


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
            "bounds_world": cast(JSONSerializable, self.bounds_world),
            "bounds_local": cast(JSONSerializable, self.bounds_local),
            "scale": self.scale,
        }


class _Serializable:
    """
    Base class for objects that have metainformation saved in `_meta.json` file.
    """

    custom_meta: dict

    def __init__(self):
        self.custom_meta = dict()

    def set_custom_meta(
        self, **custom_meta: Union[JSONSerializable, ObjectStats]
    ) -> Self:
        """
        Set custom metainformation that may be helpful when using dataset later.
        """
        for key, value in custom_meta.items():
            if isinstance(value, ObjectStats):
                value = value.to_dict()
            self.custom_meta[key] = value
        return self

    def _get_meta(self) -> dict:
        return {
            "custom_meta": self.custom_meta,
        }


class ObjectLoader:
    """
    Helper for creating object instances from a loaded Blender object source.
    """

    def __init__(
        self,
        obj,
        scene: "Scene",
        source_wrapper: Union["Object", None] = None,
    ) -> None:
        self.obj = obj
        self.scene = scene
        self.source_wrapper = source_wrapper

    def set_source(
        self,
        source: "Object",
    ) -> "ObjectLoader":
        """
        Rebind this loader to use an existing object as its instancing prototype.
        """
        if not isinstance(source, Object):
            raise TypeError("source must be Object.")
        if source.scene is not self.scene:
            raise ValueError("source object must belong to the same scene.")
        self.obj = source.obj
        self.source_wrapper = source
        return self

    def create_instance(
        self,
        name: Union[str, None] = None,
        register_object: bool = True,
        linked_data: bool = True,
    ) -> "Object":
        """
        Create a single object instance from a loader.
        """
        res = self.obj.copy()
        if not linked_data and getattr(res, "data", None) is not None:
            res.data = res.data.copy()
        _mark_object_tree(res)
        _get_generated_collection().objects.link(res)

        if name is not None:
            res.name = name

        wrapped = Object(res, self.scene, register_object=register_object)
        if self.source_wrapper is not None:
            self.source_wrapper._copy_wrapper_state_to(wrapped)
        return wrapped


class Object(_Serializable):
    """
    Wrapper around a Blender object with chainable transformation and metadata helpers.
    """

    obj: bpy.types.Object
    scene: "Scene"
    tags: TagSet
    properties: dict
    modifier_parameters: list[dict[str, JSONSerializable]]

    index: Union[int, None]

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

    def _copy_wrapper_state_to(self, other: "Object") -> None:
        other.tags = set(self.tags)
        other.properties = dict(self.properties)
        other.modifier_parameters = [
            dict(parameter) for parameter in self.modifier_parameters
        ]
        other.custom_meta = dict(self.custom_meta)

    def as_loader(self) -> ObjectLoader:
        """
        Create an `ObjectLoader` that instances this object.
        """
        return ObjectLoader(self.obj, self.scene, source_wrapper=self)

    def copy(
        self,
        name: Union[str, None] = None,
        linked_data: bool = True,
        register_object: bool = True,
    ) -> "Object":
        """
        Duplicate this object.

        If `linked_data` is False, mesh/light/camera data is copied as well.
        """
        duplicate = self.obj.copy()
        if not linked_data and getattr(duplicate, "data", None) is not None:
            duplicate.data = duplicate.data.copy()
        _mark_object_tree(duplicate)
        _get_generated_collection().objects.link(duplicate)
        if name is not None:
            duplicate.name = name
        wrapped = Object(duplicate, self.scene, register_object=register_object)
        self._copy_wrapper_state_to(wrapped)
        return wrapped

    def set_location(
        self,
        location: Union[mathutils.Vector, Sequence[float]],
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

    def get_location(self) -> Float3:
        """
        Get the object location as an `(x, y, z)` tuple.
        """
        location = self.obj.location
        return (float(location.x), float(location.y), float(location.z))

    def move(
        self,
        dx: float = 0.0,
        dy: float = 0.0,
        dz: float = 0.0,
    ) -> "Object":
        """
        Translate the object by the given offsets.
        """
        self.obj.location += mathutils.Vector((dx, dy, dz))
        return self

    def set_rotation(
        self,
        rotation: Union[mathutils.Euler, mathutils.Quaternion],
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
        scale: Union[mathutils.Vector, Sequence[float], float, int],
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
        elif not isinstance(scale, (list, tuple)):
            raise TypeError()
        elif len(scale) == 3:
            self.obj.scale = mathutils.Vector(scale)
        else:
            raise TypeError()

        return self

    def set_property(
        self,
        key: str,
        value: Any,
    ):
        """
        Set a property of the object. Properties can be used inside object's material nodes.
        """
        self.obj[key] = value
        self.properties[key] = value
        return self

    def set_modifier_input(
        self,
        input_name: str,
        value: Any,
        modifier_name: Union[str, None] = None,
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
        material: "Material",
        slot: int = 0,
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
        material: "Material",
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
        *tags: Union[str, list[str]],
    ):
        """
        Set object's tags.

        Tags are used to represent object class for training a computer vision model. Object can have more then one tag.
        """
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(
        self,
        *tags: Union[str, list[str]],
    ):
        """
        Add tags to the object.

        Tags are used to represent object class for training a computer vision model. Object can have more then one tag.
        """
        self.tags |= _combine_arglist_set(tags)
        return self

    def point_at(
        self,
        rv_obj: "Object",
        angle: float = 0.0,
    ):
        """
        Orients the current object to point at another object, with an optional rotation around the direction vector.
        """
        bpy.context.view_layer.update()
        direction = _get_object_world_location(rv_obj.obj) - _get_object_world_location(
            self.obj
        )
        rot_quat = direction.to_track_quat("-Z", "Y")
        if angle != 0.0:
            axis = direction.normalized()
            angle_quat = mathutils.Quaternion(axis, math.radians(angle))
            rot_quat = angle_quat @ rot_quat
        self.obj.rotation_quaternion = rot_quat
        return self

    def rotate_around_axis(
        self,
        axis: mathutils.Vector,
        angle: float,
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
        shading: Literal["flat", "smooth", "auto"],
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
        show=True,
    ):
        """
        Show debug axes that can be seen in the `preview` mode.
        """
        self.obj.show_axis = show
        return self

    def show_debug_name(
        self,
        show,
    ):
        """
        Show object's name that can be seen in the `preview` mode.
        """
        self.obj.show_name = show
        return self

    def hide(
        self,
        view: Literal["wireframe", "none"] = "wireframe",
    ):
        """
        Hide object from render output while controlling preview visibility.
        """
        self.obj.hide_render = True
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
        space: Literal["world", "local"] = "world",
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
        applied_scale: bool = True,
    ) -> ObjectStats:
        """
        Inspect geometric stats for this object.
        """
        return self.scene.inspect_object(self, applied_scale=applied_scale)

    def get_bounds(
        self,
        space: Literal["world", "local"] = "world",
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
        ] = "hull",
        mesh_source: Literal["BASE", "DEFORM", "FINAL"] = "FINAL",
        body_type: Literal["ACTIVE", "PASSIVE"] = "ACTIVE",
        mass: float = 1.0,
        friction: float = 0.5,
        restitution: float = 0.0,
        linear_damping: float = 0.04,
        angular_damping: float = 0.1,
        use_margin: bool = True,
        collision_margin: Union[float, None] = None,
        use_deactivation: Union[bool, None] = None,
        deactivate_linear_velocity: Union[float, None] = None,
        deactivate_angular_velocity: Union[float, None] = None,
        start_deactivated: Union[bool, None] = None,
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
        if mesh_source not in {"BASE", "DEFORM", "FINAL"}:
            raise ValueError("mesh_source must be one of: BASE, DEFORM, FINAL.")
        if collision_margin is not None and float(collision_margin) < 0:
            raise ValueError("collision_margin must be >= 0.")
        if (
            deactivate_linear_velocity is not None
            and float(deactivate_linear_velocity) < 0
        ):
            raise ValueError("deactivate_linear_velocity must be >= 0.")
        if (
            deactivate_angular_velocity is not None
            and float(deactivate_angular_velocity) < 0
        ):
            raise ValueError("deactivate_angular_velocity must be >= 0.")
        if self.obj.type != "MESH":
            raise TypeError("Rigid body is supported only for mesh objects.")
        _ensure_rigidbody_world()
        self._select_for_shading_ops()
        if self.obj.rigid_body is None:
            bpy.ops.rigidbody.object_add(type=body_type)

        rb = self.obj.rigid_body
        rb.type = body_type
        rb.collision_shape = shape_map[mode]
        _require_blender_attr(rb, "mesh_source", "rigid body mesh_source")
        rb.mesh_source = mesh_source
        rb.mass = max(float(mass), 1e-6)
        rb.friction = float(friction)
        rb.restitution = float(restitution)
        rb.linear_damping = float(linear_damping)
        rb.angular_damping = float(angular_damping)
        _require_blender_attr(rb, "use_margin", "rigid body collision margins")
        rb.use_margin = bool(use_margin)
        _require_blender_attr(rb, "collision_margin", "rigid body collision margins")
        if collision_margin is None:
            rb.collision_margin = max(0.0, min(self.get_dimensions("world")) * 0.01)
        else:
            rb.collision_margin = float(collision_margin)
        if use_deactivation is not None:
            _require_blender_attr(rb, "use_deactivation", "rigid body deactivation")
            rb.use_deactivation = bool(use_deactivation)
        if deactivate_linear_velocity is not None:
            _require_blender_attr(
                rb,
                "deactivate_linear_velocity",
                "rigid body deactivate_linear_velocity",
            )
            rb.deactivate_linear_velocity = float(deactivate_linear_velocity)
        if deactivate_angular_velocity is not None:
            _require_blender_attr(
                rb,
                "deactivate_angular_velocity",
                "rigid body deactivate_angular_velocity",
            )
            rb.deactivate_angular_velocity = float(deactivate_angular_velocity)
        if start_deactivated is not None:
            _require_blender_attr(
                rb, "use_start_deactivated", "rigid body start_deactivated"
            )
            rb.use_start_deactivated = bool(start_deactivated)
        return self

    def remove_rigidbody(
        self,
        keep_transform: bool = True,
    ) -> "Object":
        """
        Remove rigid body from this object if present.
        """
        if self.obj.rigid_body is None:
            return self

        depsgraph = bpy.context.evaluated_depsgraph_get()
        matrix = self.obj.evaluated_get(depsgraph).matrix_world.copy()
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
        angle: float,
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
        color: Color,
    ) -> Self:
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
        power: float,
    ) -> Self:
        """
        Set light power in Blender `energy` units.
        """
        if power < 0:
            raise ValueError("Light power must be non-negative.")
        self.light_data.energy = power
        return self

    def set_cast_shadow(
        self,
        enabled: bool = True,
    ) -> Self:
        """
        Enable or disable shadow casting.
        """
        self.light_data.use_shadow = enabled
        return self

    def set_specular_factor(
        self,
        factor: float,
    ) -> Self:
        """
        Set the light contribution to specular highlights.
        """
        self.light_data.specular_factor = factor
        return self

    def set_softness(
        self,
        value: float,
    ) -> Self:
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

    def set_params(self, **kwargs) -> Self:
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
        radius: float,
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
        angle: float,
    ) -> "SunLight":
        """
        Set sun angular size in degrees.
        """
        if angle < 0:
            raise ValueError("Sun light angle must be non-negative.")
        self.light_data.angle = math.radians(angle)
        return self

    def _type_specific_meta(self) -> dict:
        return {"angle_degrees": math.degrees(self.light_data.angle)}


class AreaLight(Light):
    """
    Area light with shape and size controls.
    """

    def set_shape(
        self,
        shape: Literal["SQUARE", "RECTANGLE", "DISK", "ELLIPSE"],
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
        size: float,
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
        size_x: float,
        size_y: float,
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
        angle: float,
    ) -> "SpotLight":
        """
        Set spotlight cone angle in degrees.
        """
        if angle < 0:
            raise ValueError("Spot light angle must be non-negative.")
        self.light_data.spot_size = math.radians(angle)
        return self

    def set_blend(
        self,
        blend: float,
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
        show: bool = True,
    ) -> "SpotLight":
        """
        Show or hide the spotlight cone in viewport.
        """
        self.light_data.show_cone = show
        return self

    def _type_specific_meta(self) -> dict:
        return {
            "spot_size_degrees": math.degrees(self.light_data.spot_size),
            "spot_blend": self.light_data.spot_blend,
            "show_cone": self.light_data.show_cone,
        }
