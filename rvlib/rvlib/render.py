import os
import sys
import argparse
import bpy

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from runtime_bootstrap import bootstrap_runtime  # noqa: E402


def parse_args():
    args = []
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1 :]

    parser = argparse.ArgumentParser(description="Render runner")
    parser.add_argument("--script", type=str)
    parser.add_argument("--libpath", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--number", type=int)
    parser.add_argument("--resolution", type=str, default="640,640")
    parser.add_argument("--gpu-backend", type=str, default="auto")
    parser.add_argument("--seed-mode", type=str, default="rand")
    parser.add_argument("--seed-value", type=int, default=None)
    parser.add_argument("--seed-base", type=int, default=0)
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument(
        "--noise-threshold-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--noise-threshold", type=float, default=None)
    parser.add_argument("--cwd", type=str)
    parser.add_argument("--generator-port", type=int, default=0)

    return parser.parse_args(args)


def apply_cycles_overrides(
    max_samples, min_samples, noise_threshold_enabled, noise_threshold
):
    scene_cycles = bpy.context.scene.cycles

    if max_samples is not None:
        if max_samples <= 0:
            raise ValueError("--max-samples must be > 0")
        if not hasattr(scene_cycles, "samples"):
            raise AttributeError("Blender cycles.samples is not available")
        scene_cycles.samples = max_samples

    if min_samples is not None:
        if min_samples < 0:
            raise ValueError("--min-samples must be >= 0")
        if not hasattr(scene_cycles, "adaptive_min_samples"):
            raise AttributeError("Blender cycles.adaptive_min_samples is not available")
        scene_cycles.adaptive_min_samples = min_samples

    if min_samples is not None and max_samples is not None and min_samples > max_samples:
        raise ValueError("--min-samples must be <= --max-samples")

    if noise_threshold is not None:
        if noise_threshold_enabled is not True:
            raise ValueError("--noise-threshold requires --noise-threshold-enabled=true")
        if noise_threshold <= 0:
            raise ValueError(
                "--noise-threshold must be > 0 when --noise-threshold-enabled=true"
            )

    if noise_threshold_enabled is not None:
        if not hasattr(scene_cycles, "use_adaptive_sampling"):
            raise AttributeError("Blender cycles.use_adaptive_sampling is not available")
        scene_cycles.use_adaptive_sampling = noise_threshold_enabled

    if noise_threshold_enabled is True:
        if noise_threshold is None:
            raise ValueError(
                "--noise-threshold is required when --noise-threshold-enabled=true"
            )
        if not hasattr(scene_cycles, "adaptive_threshold"):
            raise AttributeError("Blender cycles.adaptive_threshold is not available")
        scene_cycles.adaptive_threshold = noise_threshold


def run_script(
    script_path,
    output_dir,
    resolution,
    gpu_backend,
    time_limit,
    max_samples,
    min_samples,
    noise_threshold_enabled,
    noise_threshold,
    seed,
):
    import rv.internal as rvi

    scene_class = rvi._internal_load_scene_class(script_path)

    def execute_run():
        rvi._internal_begin_run(purge_orphans=True)
        instance = scene_class(output_dir)
        instance.resolution = resolution
        rvi._internal_set_time_limit(instance, time_limit)
        rvi._internal_run_scene_generate(instance, seed, ARGS.seed_mode)
        instance._internal_post_gen()
        apply_cycles_overrides(
            max_samples=max_samples,
            min_samples=min_samples,
            noise_threshold_enabled=noise_threshold_enabled,
            noise_threshold=noise_threshold,
        )
        selected_backend = rvi._internal_configure_cycles_backend(gpu_backend)
        print(f"[rv] selected_gpu_backend={selected_backend}")
        rvi._internal_print_cycles_device_info()
        instance._internal_render()
        instance._internal_save_metadata("_meta.json")
        rvi._internal_end_run(purge_orphans=False)

    execute_run()


ARGS = parse_args()

if ARGS.libpath is None:
    raise ValueError("--libpath is required")
if ARGS.cwd is None:
    raise ValueError("--cwd is required")
if ARGS.number is None:
    raise ValueError("--number is required")
if ARGS.script is None:
    raise ValueError("--script is required")

bootstrap_runtime(ARGS.libpath, ARGS.cwd)

import rv.internal as rvi  # noqa: E402

RESOLUTION = rvi._internal_parse_resolution(ARGS.resolution)
rvi._configure_generator_runtime(ARGS.generator_port, ARGS.cwd)

for i in range(ARGS.number):
    seed = rvi._internal_resolve_seed(
        ARGS.seed_mode, ARGS.seed_value, ARGS.seed_base, i
    )
    run_script(
        ARGS.script,
        ARGS.output,
        RESOLUTION,
        ARGS.gpu_backend,
        ARGS.time_limit,
        ARGS.max_samples,
        ARGS.min_samples,
        ARGS.noise_threshold_enabled,
        ARGS.noise_threshold,
        seed,
    )
