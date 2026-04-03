import bpy
import json

from .geometry import _object_world_radius
from .types import JSONSerializable
from .utils import begin_run


def _remove_blender_object(obj: bpy.types.Object) -> None:
    if obj is None:
        return
    try:
        bpy.data.objects.remove(obj, do_unlink=True)
    except Exception:
        pass


def _estimate_loader_radius(loader: "ObjectLoader", dimension: int) -> float:
    temp = loader.create_instance(register_object=False)
    try:
        return _object_world_radius(temp.obj, dimension)
    finally:
        _remove_blender_object(temp.obj)


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
    begin_run(purge_orphans=True)
