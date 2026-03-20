import argparse
import importlib.util
import inspect
import json
import os
import sys

import bpy

EXPORT_SCHEMA_VERSION = 1

CLASS_COUNT_ERROR_MESSAGE = """ERROR: exactly one class derived from rv.Scene must be defined.
Example usage:

import rv
class MyScene(rv.Scene):
    def generate(self):
        pass
"""


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Scene export runner")
    parser.add_argument("--script", type=str, required=True)
    parser.add_argument("--libpath", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--cwd", type=str, required=True)
    parser.add_argument("--freeze-physics", type=parse_bool, default=False)
    return parser.parse_args(args)


def parse_bool(raw):
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in ("true", "1", "yes", "y", "on"):
        return True
    if value in ("false", "0", "no", "n", "off"):
        return False
    raise ValueError("--freeze-physics must be true or false")


def load_scene_class(script_path):
    spec = importlib.util.spec_from_file_location("dynamic_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import rv

    scene_classes = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, rv.Scene) and obj is not rv.Scene:
            scene_classes.append(obj)

    if len(scene_classes) != 1:
        raise RuntimeError(CLASS_COUNT_ERROR_MESSAGE.strip())

    return scene_classes[0]


def set_json_prop(id_data, key, value):
    id_data[key] = json.dumps(value, sort_keys=True)


def attach_scene_metadata(scene_instance, script_path, cwd):
    scene = bpy.context.scene
    generated_collection = bpy.data.collections.get("Generated")

    scene_payload = {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "script_path": script_path,
        "cwd": cwd,
        "resolution": scene_instance.resolution,
        "time_limit": scene_instance.time_limit,
        "passes": sorted(pass_.value for pass_ in scene_instance.passes),
        "tags": sorted(scene_instance.tags),
        "semantic_channels": sorted(scene_instance.semantic_channels),
        "semantic_mask_threshold": scene_instance.semantic_mask_threshold,
        "custom_meta": scene_instance.custom_meta,
    }

    scene["rv_export_version"] = EXPORT_SCHEMA_VERSION
    scene["rv_exported"] = True
    set_json_prop(scene, "rv_scene_json", scene_payload)

    if generated_collection is not None:
        generated_collection["rv_export_version"] = EXPORT_SCHEMA_VERSION
        generated_collection["rv_generated_collection"] = True


def freeze_rigidbody_simulation():
    scene = bpy.context.scene
    frozen = []

    for obj in list(scene.objects):
        if getattr(obj, "rigid_body", None) is None:
            continue

        matrix = obj.matrix_world.copy()
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_remove()
        obj.matrix_world = matrix
        obj["rv_physics_frozen"] = True
        frozen.append(obj.name)

    if scene.rigidbody_world is not None:
        try:
            bpy.ops.object.select_all(action="DESELECT")
            bpy.ops.rigidbody.world_remove()
        except Exception:
            pass

    scene["rv_physics_frozen"] = True
    set_json_prop(
        scene,
        "rv_physics_freeze_json",
        {
            "frozen_objects": frozen,
            "frame": int(scene.frame_current),
            "method": "final_transform_snapshot",
        },
    )


def attach_object_metadata(scene_instance):
    wrappers = list(scene_instance.objects) + list(scene_instance.lights)
    seen = set()

    for wrapper in wrappers:
        obj = wrapper.obj
        ptr = obj.as_pointer()
        if ptr in seen:
            continue
        seen.add(ptr)

        obj["rv_export_version"] = EXPORT_SCHEMA_VERSION
        obj["rv_generated"] = True
        if wrapper.index is not None:
            obj["rv_object_index"] = wrapper.index
        set_json_prop(obj, "rv_tags_json", sorted(wrapper.tags))
        set_json_prop(obj, "rv_object_json", wrapper._get_meta())


def attach_material_metadata(scene_instance):
    for material in scene_instance.materials:
        bpy_material = material._resolved_material
        if bpy_material is None:
            continue
        bpy_material["rv_export_version"] = EXPORT_SCHEMA_VERSION
        bpy_material["rv_generated"] = True
        if material.index is not None:
            bpy_material["rv_material_index"] = material.index
        set_json_prop(bpy_material, "rv_material_json", material._get_meta())


def save_scene(output_path):
    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_path, copy=False)


def main():
    args = parse_args()

    sys.path.insert(0, args.libpath)
    sys.path.insert(0, args.cwd)
    os.chdir(args.cwd)

    scene_class = load_scene_class(args.script)

    import rv

    rv.begin_run(purge_orphans=True)
    scene_instance = scene_class(output_dir=None)
    scene_instance.generate()
    scene_instance._post_gen()

    if args.freeze_physics:
        freeze_rigidbody_simulation()

    attach_scene_metadata(scene_instance, args.script, args.cwd)
    attach_object_metadata(scene_instance)
    attach_material_metadata(scene_instance)
    save_scene(args.output)
    rv.end_run(purge_orphans=False)


if __name__ == "__main__":
    main()
