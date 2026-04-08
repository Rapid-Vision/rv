import importlib.util
import inspect
import random
import uuid

import bpy

from .passes import PASS_MAP, RenderPass
from .types import (
    AABB,
    CellCoords,
    Color,
    ColorRGB,
    ColorRGBA,
    Float2,
    Float3,
    Float4,
    JSONSerializable,
    ObjectLoaderSource,
    OptionalColor,
    Polygon2D,
    RenderPassSet,
    Resolution,
    ScatterValidationResult,
    SemanticChannelSet,
    TagSet,
)

_RV_OWNED_KEY = "_rv_owned"
_RV_RUN_ID_KEY = "_rv_run_id"
_ACTIVE_RUN_ID = None
_INTERNAL_CLASS_COUNT_ERROR_MESSAGE = """ERROR: exactly one class derived from rv.Scene must be defined.
Example usage:

import rv
class MyScene(rv.Scene):
    def generate(self, seed):
        pass
"""
_INTERNAL_VALID_GPU_BACKENDS = ("auto", "optix", "cuda", "hip", "oneapi", "metal", "cpu")


def _as_rgba(color: Color) -> ColorRGBA:
    rgba = tuple(float(component) for component in color)
    if len(rgba) == 3:
        return (rgba[0], rgba[1], rgba[2], 1.0)
    if len(rgba) != 4:
        raise TypeError("Color must have 3 (RGB) or 4 (RGBA) components.")
    return rgba


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


def _require_blender_attr(target, attr: str, feature: str) -> None:
    if not hasattr(target, attr):
        raise RuntimeError(f"Blender does not support {feature}.")


def _internal_parse_resolution(raw, arg_name: str = "--resolution") -> Resolution:
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"{arg_name} must be WIDTH,HEIGHT")
    width = int(parts[0])
    height = int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError(f"{arg_name} width and height must be > 0")
    return (width, height)


def _internal_load_scene_class(script_path: str):
    spec = importlib.util.spec_from_file_location("dynamic_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load scene script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import rv

    scene_classes = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, rv.Scene) and obj is not rv.Scene:
            scene_classes.append(obj)

    if len(scene_classes) != 1:
        raise RuntimeError(_INTERNAL_CLASS_COUNT_ERROR_MESSAGE.strip())

    return scene_classes[0]


def _internal_run_scene_generate(
    scene_instance, seed: int | None, seed_mode: str | None = None
) -> None:
    scene_instance.seed = seed
    scene_instance.seed_mode = seed_mode
    print(f"[rv] seed={seed}")
    generate = scene_instance.generate
    signature = inspect.signature(generate)
    positional_params = [
        param
        for param in signature.parameters.values()
        if param.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
    ]

    if positional_params:
        generate(seed)
        return

    generate()


def _internal_resolve_seed(
    seed_mode: str, seed_value: int | None = None, seed_base: int = 0, index: int = 0
) -> int:
    if seed_mode in ("rand", "random"):
        return random.SystemRandom().randrange(0, 2**63)
    if seed_mode == "seq":
        return seed_base + index
    if seed_mode == "fixed":
        if seed_value is None:
            raise ValueError("seed_value is required for fixed seed mode")
        return seed_value
    raise ValueError(f"Unsupported seed mode: {seed_mode}")


def _internal_iter_cycles_devices(preferences):
    devices = getattr(preferences, "devices", None)
    if devices:
        return list(devices)

    get_devices = getattr(preferences, "get_devices", None)
    if callable(get_devices):
        groups = get_devices() or []
        flattened = []
        for group in groups:
            if group:
                flattened.extend(group)
        return flattened

    return []


def _internal_configure_cycles_backend(requested_backend: str) -> str:
    scene = bpy.context.scene
    scene.cycles.device = "GPU"

    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
    except KeyError as exc:
        raise RuntimeError("Cycles add-on preferences are unavailable") from exc

    refresh_devices = getattr(preferences, "refresh_devices", None)
    if callable(refresh_devices):
        refresh_devices()

    requested = requested_backend.strip().lower()
    if requested not in _INTERNAL_VALID_GPU_BACKENDS:
        raise ValueError(
            "--gpu-backend must be one of auto, optix, cuda, hip, oneapi, metal, cpu"
        )

    available_types = {
        device.type for device in _internal_iter_cycles_devices(preferences)
    }
    if requested == "auto":
        for backend in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
            if backend in available_types:
                requested = backend.lower()
                break
        else:
            requested = "cpu"

    if requested == "cpu":
        scene.cycles.device = "CPU"
        return "CPU"

    selected_type = requested.upper()
    if selected_type not in available_types:
        available = sorted(available_types) or ["CPU"]
        raise RuntimeError(
            f"Requested GPU backend {selected_type} is unavailable. "
            f"Available device types: {', '.join(available)}"
        )

    preferences.compute_device_type = selected_type
    if callable(refresh_devices):
        refresh_devices()

    enabled_gpu = False
    for device in _internal_iter_cycles_devices(preferences):
        is_matching_gpu = device.type == selected_type
        if hasattr(device, "use"):
            device.use = is_matching_gpu
        if is_matching_gpu:
            enabled_gpu = True

    if not enabled_gpu:
        raise RuntimeError(f"Requested GPU backend {selected_type} found no enabled devices")

    scene.cycles.device = "GPU"
    return selected_type


def _internal_print_cycles_device_info() -> None:
    scene = bpy.context.scene
    print(f"[rv] engine={scene.render.engine}")
    print(f"[rv] cycles_device={scene.cycles.device}")

    try:
        preferences = bpy.context.preferences.addons["cycles"].preferences
    except KeyError:
        print("[rv] cycles_preferences=unavailable")
        return

    refresh_devices = getattr(preferences, "refresh_devices", None)
    if callable(refresh_devices):
        refresh_devices()

    print(
        f"[rv] compute_device_type={getattr(preferences, 'compute_device_type', None)}"
    )

    devices = _internal_iter_cycles_devices(preferences)
    if not devices:
        print("[rv] devices=[]")
        return

    serialized_devices = [
        {
            "name": device.name,
            "type": device.type,
            "use": getattr(device, "use", None),
        }
        for device in devices
    ]
    print(f"[rv] devices={serialized_devices}")


def _internal_set_time_limit(scene_instance, time_limit: float | None) -> None:
    if time_limit is None:
        return
    if time_limit <= 0:
        raise ValueError("--time-limit must be > 0")
    scene_instance.time_limit = time_limit


def _internal_begin_run(purge_orphans: bool = True) -> str:
    global _ACTIVE_RUN_ID
    _remove_rv_data()
    if purge_orphans:
        _purge_orphans()
    _ACTIVE_RUN_ID = uuid.uuid4().hex
    return _ACTIVE_RUN_ID


def _internal_end_run(purge_orphans: bool = False) -> None:
    if purge_orphans:
        _purge_orphans()
