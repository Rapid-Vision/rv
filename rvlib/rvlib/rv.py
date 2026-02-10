"""
Module for describing an `rv` scenes. To create a scene implement a class derrived from `Scene`.

- To preview scene use the `rv preview <scene.py>` command.
- To render resulting dataset use the `rv render <scene.py>` command.

### Scene example
Here is a basic non-random scene with a cube and a sphere.
To preview resulting segmentation masks see the `PreviewIndexOB0001.png` after rendering.
```
class BasicScene(rv.Scene):
    def generate(self):
        self.get_world().set_params(sun_intensity=0.03)
        cube = (
            self.create_cube().set_location((1, 0, 0.5)).set_scale(0.5).set_tags("cube")
        )
        sphere = (
            self.create_sphere()
            .set_location((-1, 0, 1))
            .set_shading("smooth")
            .set_tags("sphere")
        )
        plane = self.create_plane(size=1000)
        empty = self.create_empty().set_location((0, 0, 1))

        cam = self.get_camera().set_location((7, 7, 3)).point_at(empty)
```

### Results
| Image | Segmentation |
| :-: | :-: |
| ![resulting image](/examples/1_primitives/1_res.png) | ![resulting image](/examples/1_primitives/1_segs.png)|
"""

from abc import ABC, abstractmethod
import typing
from mathutils import Vector
from typing import Literal, Union, Optional
import bpy
import bpy_extras
import json
import math
import os
import pathlib
import uuid
import mathutils
from enum import Enum

JSONSerializable = Union[
    str, int, float, bool, None, list["json.JSONType"], dict[str, "json.JSONType"]
]


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

    if (
        scene.compositing_node_group is not None
        and _is_owned(scene.compositing_node_group)
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
        bpy.data.orphans_purge(do_local_ids=True, do_linked_ids=False, do_recursive=True)
    except TypeError:
        try:
            bpy.data.orphans_purge()
        except Exception:
            pass
    except Exception:
        pass


def begin_run(purge_orphans: bool = True) -> str:
    global _ACTIVE_RUN_ID
    _remove_rv_data()
    if purge_orphans:
        _purge_orphans()
    _ACTIVE_RUN_ID = uuid.uuid4().hex
    return _ACTIVE_RUN_ID


def end_run(purge_orphans: bool = False) -> None:
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

    def set_custom_meta(self, **custom_meta: dict[str, JSONSerializable]) -> None:
        """
        Set custom metainformation that may be helpful when using dataset later.
        """
        for key, value in custom_meta.items():
            self.custom_meta[key] = value

    def _get_meta(self) -> dict:
        return {
            "custom_meta": self.custom_meta,
        }


class Scene(ABC, _Serializable):
    """
    Base class for describing rv scene. To set up a scene, implement `generate` function.
    """

    resolution: tuple[int, int] = (640, 640)
    time_limit: float = 3.0
    passes: set[RenderPass] = None
    output_dir: Optional[
        str
    ]  # Directory for storing all outputs generated by a single `rv render` run
    subdir: str  # Directory to store results of a single rendering
    camera: "Camera"
    world: "World"
    tags: set[str]

    objects: set["Object"]

    object_index_counter: int = 0

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
        self.objects = set()
        self.tags = set()

        _get_generated_collection()
        bpy.ops.object.camera_add()
        _move_object_to_generated_collection(bpy.context.active_object)
        _mark_object_tree(bpy.context.active_object)
        self.camera = Camera(bpy.context.active_object, self)
        bpy.context.scene.camera = self.camera.obj
        self.camera.set_location(mathutils.Vector((0, 0, 10)))
        self._set_user_view()

        self.world = WorldSky()

    def set_resolution(self, width: float, height: float = None):
        """
        Set resulting image resolution. If only width is passed, resulting image will be a square.
        """
        if height is None:
            height = width
        self.resolution = (width, height)
        return self

    def set_rendering_time_limit(
        self,
        time_limit: float = 3.0,  # Rendering time limit in seconds
    ):
        """
        Set the maximum allowed rendering time for a single image. Higher value leads to better quality.
        """
        self.time_limit = time_limit
        return self

    def set_passes(self, *passes: tuple[RenderPass | list[RenderPass], ...]):
        """
        Set a list of render passes that will be saved when rendering.
        """
        self.passes = _combine_arglist_set(passes)
        return self

    def create_empty(self, name: str = "Empty") -> "Object":
        """
        Create an empty object. May be useful to point camera at or for debugging during `preview` stage.
        """
        empty = bpy.data.objects.new(name, None)
        _mark_object_tree(empty)
        _get_generated_collection().objects.link(empty)

        return Object(empty, self)

    def create_sphere(
        self,
        name: str = "Sphere",
        radius: float = 1.0,
        segments: int = 32,
        ring_count: int = 16,
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

    def create_cube(self, name: str = "Cube", size: float = 2.0) -> "Object":
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
        name: str = "Plane",
        size: float = 2.0,
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

    def get_camera(self) -> "Camera":
        """
        Get the `Camera` object used for rendering.
        """
        return self.camera

    def set_world(self, world: "World") -> "World":
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

    def set_tags(self, *tags) -> "Scene":
        """
        Set scene's global tags.

        Tags are used to represent image class for training a computer vision model for a classification task.
        """
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(self, *tags) -> "Scene":
        """
        Add tags to the scene.

        Tags are used to represent image class for training a computer vision model for a classification task.
        """
        self.tags |= _combine_arglist_set(tags)
        return self

    def load_object(self, blendfile: str, import_name: str = None) -> "ObjectLoader":
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
        self, blendfile: str, import_names: list[str] = None
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
        _configure_passes(self.passes)

        if self.output_dir is None:
            _configure_compositor(None)
        else:
            self.subdir = str(uuid.uuid4())
            _configure_compositor(os.path.join(self.output_dir, self.subdir))

    def _render(self) -> None:
        if self.output_dir is not None:
            bpy.ops.render.render(write_still=False)

    def _register_object(self, obj: "Object") -> int:
        self.object_index_counter += 1
        self.objects.add(obj)
        return self.object_index_counter

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "resolution": self.resolution,
                "time_limit": self.time_limit,
                "passes": [p.value for p in self.passes],
                "tags": list(self.tags),
                "objects": list(obj._get_meta() for obj in self.objects),
            }
        )
        return res

    def _save_metadata(self, filename: str) -> None:
        with open(os.path.join(self.output_dir, self.subdir, filename), "w") as fout:
            json.dump(self._get_meta(), fout, indent=4)


class ObjectLoader:
    def __init__(self, obj, scene: "Scene") -> None:
        self.obj = obj
        self.scene = scene

    def create_instance(
        self,
        name: str = None,  # Instanced object name
    ) -> "Object":
        """
        Create a single object instance from a loader.
        """
        res = self.obj.copy()
        _mark_object_tree(res)
        _get_generated_collection().objects.link(res)

        if name is not None:
            res.name = name

        return Object(res, self.scene)


class Object(_Serializable):
    obj: bpy.types.Object
    scene: Scene
    tags: set[str]
    properties: dict

    index: int

    def __init__(self, obj: bpy.types.Object, scene: "Scene") -> None:
        super().__init__()

        self.obj = obj
        self.scene = scene

        self.tags = set()
        self.properties = dict()

        self.index = self.scene._register_object(self)
        self.obj.pass_index = self.index
        self.obj.rotation_mode = "QUATERNION"

    def set_location(self, location: Union[mathutils.Vector, typing.Sequence[float]]):
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

    def set_rotation(self, rotation: Union[mathutils.Euler, mathutils.Quaternion]):
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

    def set_scale(self, scale: Union[mathutils.Vector, typing.Sequence[float], float]):
        """
        Set the scale of the object.

        If `scale` is a single float, all axes are set to that value.
        If `scale` is a sequence or Vector of length 3, each axis is set individually.
        """
        if isinstance(scale, mathutils.Vector):
            self.obj.scale = scale
        elif isinstance(scale, float):
            self.obj.scale = mathutils.Vector((scale, scale, scale))
        elif len(scale) == 3:
            self.obj.scale = mathutils.Vector(scale)
        else:
            raise TypeError()

        return self

    def set_property(self, key: str, value: any):
        """
        Set a property of the object. Properties can be used inside object's material nodes.
        """
        self.obj[key] = value
        self.properties[key] = value
        return self

    def set_tags(self, *tags: str | list[str]):
        """
        Set object's tags.

        Tags are used to represent object class for training a computer vision model. Object can have more then one tag.
        """
        self.tags = _combine_arglist_set(tags)
        return self

    def add_tags(self, *tags: str | list[str]):
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

    def set_shading(self, shading: Literal["flat", "smooth"]):
        """
        Set shading to flat or smooth.
        """
        bpy.ops.object.select_all(action="DESELECT")
        self.obj.select_set(True)

        if shading == "flat":
            bpy.ops.object.shade_flat()
        elif shading == "smooth":
            bpy.ops.object.shade_smooth()
        else:
            raise ValueError(f"Unknown shading mode: {shading}")

        return self

    def show_debug_axes(self, show=True):
        """
        Show debug axes that can be seen in the `preview` mode.
        """
        self.obj.show_axis = show
        return self

    def show_debug_name(self, show):
        """
        Show object's name that can be seen in the `preview` mode.
        """
        self.obj.show_name = show
        return self

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "index": self.index,
                "name": self.obj.name,
                "tags": list(self.tags),
                "properties": self.properties,
                "location": tuple(self.obj.location),
                "rotation": tuple(self.obj.rotation_euler),
                "scale": tuple(self.obj.scale),
            }
        )
        return res


class Camera(Object):
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
        pass


class WorldColor(World):
    """
    `World` class representing a single color environmental lighting.
    """

    color: tuple[float, float, float, float] = None
    strength: float = None

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
        color: tuple[float, float, float, float] = None,  # environement color
        strength: float = None,  # envronement light strength
    ):
        """
        Set ligthing parameters.
        """
        if color is not None:
            self.color = color
        if strength is not None:
            self.strength = strength


class WorldSky(World):
    """
    `World` class representing a procedural sky environement.

    For more information, view [official blender docs](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/sky.html).
    """

    strength: float = None

    sun_size: float = None
    sun_intensity: float = None

    sun_elevation: float = None
    rotation_z: float = None

    altitude: float = None

    air: float = 0.1
    aerosol_density: float = 0.01
    ozone: float = 10.0

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


class WorldHDRI(World):
    """
    `World` class for importing lighting from an hdri `.exr` file.

    HDRI files can be captured by a 360 camera or a smartphone app or downloaded from public libraries such as [polyhaven](https://polyhaven.com/hdris).
    """

    hdri_path: str
    strength: float = None
    rotation_z: float = None

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
            node_env_tex.image = bpy.data.images.load(self.hdri_path, check_existing=False)
            _mark_owned(node_env_tex.image)

        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength

        if self.rotation_z is not None:
            node_mapping.inputs["Rotation"].default_value[2] = self.rotation_z

    def set_params(
        self,
        hdri_path: str = None,  # Path to the `.exr` file
        strength: float = None,  #
        rotation_z: float = None,
    ):
        if hdri_path is not None:
            self.hdri_path = hdri_path
        if strength is not None:
            self.strength = strength
        if rotation_z is not None:
            self.rotation_z = rotation_z


class WorldImported(World):
    """
    `World` class for importing environment lighting from a `.blend` file.

    Use it to bring in custom procedural lighting setups and adjust their parameters by the script.
    """

    filepath: str
    world_name: str = None
    params: dict

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
        self.params.update(kwargs)


def _use_cycles() -> None:
    if bpy.context.scene.render.engine != "CYCLES":
        bpy.context.scene.render.engine = "CYCLES"


def _use_gpu():
    if bpy.context.scene.cycles.device != "GPU":
        bpy.context.scene.cycles.device = "GPU"


def _deselect():
    bpy.ops.object.select_all(action="DESELECT")


def _set_resolution(resolution: tuple[int, int]):
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100


def _set_time_limit(time_limit: float):
    bpy.context.scene.cycles.time_limit = time_limit


def _configure_passes(passes: set[RenderPass]):
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


def _configure_compositor(
    output_dir: str,  # Directory where rendered output files will be saved
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
    index_file_out_node.location = (2 * dx, -350)
    _reset_file_output_node(index_file_out_node, output_dir)
    _configure_file_output_node_format(
        index_file_out_node,
        file_format="PNG",
        color_mode="RGB",
        color_depth="16",
    )

    index_ob = _find_socket_by_name(render_layers.outputs, "Object Index")
    index_ma = _find_socket_by_name(render_layers.outputs, "Material Index")
    index_sockets = [index_ob, index_ma]

    for output in render_layers.outputs:
        if output in index_sockets:
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


def _combine_arglist_set(args):
    result = set()
    for p in args:
        if isinstance(p, list):
            result = result.union(set(p))
        else:
            result.add(p)
    return result


def _clear_scene():
    # Backward-compatible entrypoint used by older scripts.
    begin_run(purge_orphans=True)
