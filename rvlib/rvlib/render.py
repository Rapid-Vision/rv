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
    parser.add_argument("--cwd", type=str)

    return parser.parse_args(args)


def parse_resolution(raw):
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) != 2:
        raise ValueError("--resolution must be WIDTH,HEIGHT")
    width = int(parts[0])
    height = int(parts[1])
    if width <= 0 or height <= 0:
        raise ValueError("--resolution width and height must be > 0")
    return (width, height)


def run_script(script_path, output_dir, resolution):
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
        instance.generate()
        instance._post_gen()
        instance._render()
        instance._save_metadata("_meta.json")
        rv.end_run(purge_orphans=False)

    run_script()


ARGS = parse_args()
RESOLUTION = parse_resolution(ARGS.resolution)

sys.path.append(ARGS.libpath)
os.chdir(ARGS.cwd)

for i in range(ARGS.number):
    run_script(ARGS.script, ARGS.output, RESOLUTION)
