import os
import uuid
import bpy

PASS_MAP = {
    # Core buffers
    "Z":                     "use_pass_z",
    "Vector":                "use_pass_vector",
    "Mist":                  "use_pass_mist",
    "Normal":                "use_pass_normal",
    "UV":                    "use_pass_uv",
    "ObjectIndex":           "use_pass_object_index",
    "MaterialIndex":         "use_pass_material_index",
    "Shadow":                "use_pass_shadow",

    # Lighting / surface components
    "AO":                    "use_pass_ambient_occlusion",
    "Emission":              "use_pass_emit",
    "Environment":           "use_pass_environment",
    "ShadowCatcher":         "use_pass_shadow_catcher",

    # Diffuse
    "DiffuseColor":          "use_pass_diffuse_color",
    "DiffuseDirect":         "use_pass_diffuse_direct",
    "DiffuseIndirect":       "use_pass_diffuse_indirect",

    # Glossy
    "GlossyColor":           "use_pass_glossy_color",
    "GlossyDirect":          "use_pass_glossy_direct",
    "GlossyIndirect":        "use_pass_glossy_indirect",

    # Transmission
    "TransmissionColor":     "use_pass_transmission_color",
    "TransmissionDirect":    "use_pass_transmission_direct",
    "TransmissionIndirect":  "use_pass_transmission_indirect",

    # Volume
    "VolumeDirect":          "use_pass_volume_direct",
    "VolumeIndirect":        "use_pass_volume_indirect",

    # Cryptomatte (Blender ≥ 3.0)
    "CryptoObject":          "use_pass_cryptomatte_object",
    "CryptoMaterial":        "use_pass_cryptomatte_material",
    "CryptoAsset":           "use_pass_cryptomatte_asset",
} # Map pass names to corresponding attribute names


"""
List all available pass names
"""
def list_passes():
    return PASS_MAP.keys()

class Scene:
    """
Base class for describing rv scene. To set up a scene, reimplement `generate` function.

Example scene:
```
class MyScene(rv.Scene):
    def generate(self):
        # generate scene
```
    """


    resolution: tuple[int, int] = (640, 640)
    passes: list = ["Combined"]
    output_dir: str

    def __init__(self, output_dir):
        self.output_dir = output_dir

    def generate(self):
        pass

    def set_resolution(self, width, height=None):
        if height is None:
            height = width
        self.resolution = (width, height)


    def set_passes(self, passes: list):
        self.passes = list({"Combined"}.union(set(passes)))

    def _post_gen(self):
        _set_resolution(self.resolution)
        _use_gpu()
        _use_cycles()
        _configure_passes(self.passes)

        subdir = str(uuid.uuid4())
        _configure_compositor(os.path.join(self.output_dir, subdir), self.passes)

    def _render(self):
        bpy.ops.render.render(write_still=False)


def _use_cycles():
    if bpy.context.scene.render.engine != "CYCLES":
        bpy.context.scene.render.engine = "CYCLES"

def _use_gpu():
    if bpy.context.scene.cycles.device != 'GPU':
        bpy.context.scene.cycles.device = 'GPU'

def _set_resolution(resolution: tuple[int, int]):
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100


def _configure_passes(passes: list):
    """
    Enable/disable Cycles render-passes according to passes list.

    To get list of names of all available passes use `list_passes` function
    """
    layer = bpy.context.view_layer

    # 1) Disable *every* pass first to get a clean slate
    for attr in PASS_MAP.values():
        if hasattr(layer, attr):
            setattr(layer, attr, False)

    # 2) Turn on requested passes
    for p in passes:
        if p == "Combined": # always present
            continue
        attr = PASS_MAP.get(p)
        if attr and hasattr(layer, attr):
            setattr(layer, attr, True)
        else:
            print(f"[rv] Warning: unknown or unsupported pass '{p}' – skipped.")

    # 3) We always need Object-Index for segmentation masks
    layer.use_pass_object_index = True


def _configure_compositor(output_dir: str, passes: list):
    bpy.context.scene.use_nodes = True
    tree = bpy.context.scene.node_tree
    tree.nodes.clear()
    tree.links.clear()

    render_layers = tree.nodes.new("CompositorNodeRLayers")
    render_layers.location = (0, 0)

    comp = tree.nodes.new("CompositorNodeComposite")

    dx, dy = 350, 100
    comp.location = (dx, dy)
    tree.links.new(render_layers.outputs["Image"], comp.inputs["Image"])

    for i, output in enumerate(render_layers.outputs):
        name = output.name
        if name not in render_layers.outputs:
            continue

        file_out_node = tree.nodes.new("CompositorNodeOutputFile")
        file_out_node.location = (dx, -dy * i)
        file_out_node.base_path = output_dir
        file_out_node.label = name
        file_out_node.file_slots.clear()

        slot = file_out_node.file_slots.new(name)

        tree.links.new(render_layers.outputs[name], file_out_node.inputs[name])
