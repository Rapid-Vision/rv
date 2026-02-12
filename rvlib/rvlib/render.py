import importlib.util
import inspect
import os
import sys
import argparse
import bpy

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

    parser = argparse.ArgumentParser(description="Render runner")
    parser.add_argument("--script", type=str)
    parser.add_argument("--libpath", type=str)
    parser.add_argument("--output", type=str)
    parser.add_argument("--number", type=int)
    parser.add_argument("--resolution", type=str, default="640,640")
    parser.add_argument("--time-limit", type=float, default=None)
    parser.add_argument("--max-samples", type=int, default=None)
    parser.add_argument("--min-samples", type=int, default=None)
    parser.add_argument("--noise-threshold-enabled", type=parse_bool, default=None)
    parser.add_argument("--noise-threshold", type=float, default=None)
    parser.add_argument("--cwd", type=str)

    return parser.parse_args(args)


def parse_bool(raw):
    if isinstance(raw, bool):
        return raw
    value = str(raw).strip().lower()
    if value in ("true", "1", "yes", "y", "on"):
        return True
    if value in ("false", "0", "no", "n", "off"):
        return False
    raise ValueError("--noise-threshold-enabled must be true or false")


def parse_resolution(raw):
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 2:
        raise ValueError("--resolution must be WIDTH,HEIGHT")
    width = int(parts[0])
    height = int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--resolution width and height must be > 0")
    return (width, height)


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
    time_limit,
    max_samples,
    min_samples,
    noise_threshold_enabled,
    noise_threshold,
):
    spec = importlib.util.spec_from_file_location("dynamic_module", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    import rv

    scene_classes = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if issubclass(obj, rv.Scene) and obj is not rv.Scene:
            scene_classes.append(obj)

    if len(scene_classes) != 1:
        print(CLASS_COUNT_ERROR_MESSAGE)
        return

    def run_script():
        rv.begin_run(purge_orphans=True)
        instance = scene_classes[0](output_dir)
        instance.resolution = resolution
        if time_limit is not None:
            if time_limit <= 0:
                raise ValueError("--time-limit must be > 0")
            instance.time_limit = time_limit
        instance.generate()
        instance._post_gen()
        apply_cycles_overrides(
            max_samples=max_samples,
            min_samples=min_samples,
            noise_threshold_enabled=noise_threshold_enabled,
            noise_threshold=noise_threshold,
        )
        instance._render()
        instance._save_metadata("_meta.json")
        rv.end_run(purge_orphans=False)

    run_script()


ARGS = parse_args()
RESOLUTION = parse_resolution(ARGS.resolution)

sys.path.append(ARGS.libpath)
os.chdir(ARGS.cwd)

for i in range(ARGS.number):
    run_script(
        ARGS.script,
        ARGS.output,
        RESOLUTION,
        ARGS.time_limit,
        ARGS.max_samples,
        ARGS.min_samples,
        ARGS.noise_threshold_enabled,
        ARGS.noise_threshold,
    )
