import importlib.util
import inspect
import sys
import argparse
import bpy

CLASS_COUNT_ERROR_MESSAGE="""ERROR: exactly one class derived from rv.Scene must be defined.
Example usage:

import rv
class MyScene(rv.Scene):
    def generate(self):
        pass
"""

def parse_args():
    args = []
    if '--' in sys.argv:
        args = sys.argv[sys.argv.index('--') + 1:]

    parser = argparse.ArgumentParser(description="Render runner")
    parser.add_argument('--script', type=str)
    parser.add_argument('--libpath', type=str)
    parser.add_argument('--output', type=str)
    parser.add_argument('--number', type=int)

    return parser.parse_args(args)

def run_script(script_path, output_dir):
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
        clear()
        try:
            instance = scene_classes[0](output_dir)
            instance.generate()
            instance._post_gen()
            instance._render()
        except BaseException as e:
            print(f"ERROR: An exception occurred while running the script: {e}")

    run_script()

def clear():
    if "Generated" not in bpy.data.collections:
        bpy.data.collections.new("Generated")
        bpy.context.scene.collection.children.link(bpy.data.collections["Generated"])
    collection = bpy.data.collections["Generated"]
    for obj in collection.objects:
        bpy.data.objects.remove(obj, do_unlink=True)

ARGS = parse_args()

sys.path.append(ARGS.libpath)
run_script(ARGS.script, ARGS.output)