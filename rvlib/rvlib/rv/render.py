import bpy

from .compositor import _configure_semantic_aovs
from .passes import PASS_MAP
from .types import RenderPassSet, Resolution, SemanticChannelSet
from .utils import _require_blender_attr


def _use_cycles() -> None:
    if bpy.context.scene.render.engine != "CYCLES":
        bpy.context.scene.render.engine = "CYCLES"


def _use_gpu():
    if bpy.context.scene.cycles.device != "GPU":
        bpy.context.scene.cycles.device = "GPU"


def _deselect():
    bpy.ops.object.select_all(action="DESELECT")


def _set_resolution(resolution: Resolution):
    scene = bpy.context.scene
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100


def _set_time_limit(time_limit: float):
    bpy.context.scene.cycles.time_limit = time_limit


def _configure_passes(
    passes: RenderPassSet, semantic_channels: SemanticChannelSet | None = None
):
    """
    Enable/disable Cycles render-passes according to the `passes` list.
    """
    layer = bpy.context.view_layer

    for attr in PASS_MAP.values():
        if hasattr(layer, attr):
            setattr(layer, attr, False)

    for p in passes:
        pass_attr = PASS_MAP.get(p)
        if not pass_attr:
            raise RuntimeError(f"Unknown render pass '{p.name}'.")
        _require_blender_attr(layer, pass_attr, f"render pass {p.name}")
        setattr(layer, pass_attr, True)

    _require_blender_attr(layer, "use_pass_object_index", "render pass OBJECT_INDEX")
    layer.use_pass_object_index = True

    _configure_semantic_aovs(layer, semantic_channels or set())
