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
