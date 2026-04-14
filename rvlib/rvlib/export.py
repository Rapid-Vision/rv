import argparse
import json
import os
import sys

import bpy

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from runtime_bootstrap import bootstrap_runtime

EXPORT_SCHEMA_VERSION = 1


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Scene export runner")
    parser.add_argument("--script", type=str, required=True)
    parser.add_argument("--libpath", type=str, required=True)
    parser.add_argument("--output", type=str, required=True)
    parser.add_argument("--cwd", type=str, required=True)
    parser.add_argument("--seed-mode", type=str, default="rand")
    parser.add_argument("--seed-value", type=int, default=None)
    parser.add_argument("--freeze-physics", action="store_true")
    parser.add_argument("--pack-resources", action="store_true")
    parser.add_argument("--generator-port", type=int, default=0)
    return parser.parse_args(args)


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
        "seed": scene_instance.seed,
        "seed_mode": scene_instance.seed_mode,
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
    depsgraph = bpy.context.evaluated_depsgraph_get()
    frozen = []

    for obj in list(scene.objects):
        if getattr(obj, "rigid_body", None) is None:
            continue

        matrix = obj.evaluated_get(depsgraph).matrix_world.copy()
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
    wrappers = list(scene_instance.generated_objects) + list(
        scene_instance.generated_lights
    )
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
    for material in scene_instance.generated_materials:
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


def pack_resources():
    bpy.ops.file.pack_all()


def main():
    args = parse_args()

    bootstrap_runtime(args.libpath, args.cwd)

    import rv
    import rv.internal as rvi

    rvi._configure_generator_runtime(args.generator_port, args.cwd)
    scene_class = rvi._internal_load_scene_class(args.script)
    rvi._internal_begin_run(purge_orphans=True)
    scene_instance = scene_class(output_dir=None)
    seed = rvi._internal_resolve_seed(args.seed_mode, args.seed_value)
    rvi._internal_run_scene_generate(scene_instance, seed, args.seed_mode)
    scene_instance._internal_post_gen()

    if args.freeze_physics:
        freeze_rigidbody_simulation()
    if args.pack_resources:
        pack_resources()

    attach_scene_metadata(scene_instance, args.script, args.cwd)
    attach_object_metadata(scene_instance)
    attach_material_metadata(scene_instance)
    save_scene(args.output)
    rvi._internal_end_run(purge_orphans=False)


if __name__ == "__main__":
    main()
