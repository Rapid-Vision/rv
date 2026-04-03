import typing

import bpy

from .material import _normalize_semantic_channel, _semantic_aov_name
from .types import SemanticChannelSet
from .utils import _mark_node_tree, _require_blender_attr


def _configure_semantic_aovs(layer, semantic_channels: SemanticChannelSet) -> None:
    if not semantic_channels:
        return
    _require_blender_attr(layer, "aovs", "semantic AOV channels")

    for aov in list(layer.aovs):
        aov_name = getattr(aov, "name", "")
        if _normalize_socket_name(aov_name) in semantic_channels:
            layer.aovs.remove(aov)

    for channel in sorted(semantic_channels):
        aov = layer.aovs.add()
        aov.name = _semantic_aov_name(channel)
        if hasattr(aov, "type"):
            aov.type = "VALUE"


def _configure_compositor(
    output_dir: str,
    semantic_channels: SemanticChannelSet | None = None,
    semantic_mask_threshold: float = 0.5,
) -> None:
    """
    Configure compositor nodes in Blender 5 for saving render outputs.
    """
    scene = bpy.context.scene
    tree = _get_compositor_tree(scene)
    tree.nodes.clear()
    tree.links.clear()

    dx, dy = 350, 60

    render_layers = tree.nodes.new(type="CompositorNodeRLayers")
    render_layers.location = (0, 0)

    _connect_group_output_image(tree, render_layers, dx, dy)

    file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    file_out_node.location = (2 * dx, 0)
    _reset_file_output_node(file_out_node, output_dir)
    _configure_file_output_node_format(
        file_out_node,
        file_format="PNG",
        color_mode="RGBA",
        color_depth="8",
    )

    index_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    index_file_out_node.location = (2 * dx + 40, -350)
    _reset_file_output_node(index_file_out_node, output_dir)
    _configure_file_output_node_format(
        index_file_out_node,
        file_format="PNG",
        color_mode="RGB",
        color_depth="16",
    )

    semantic_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    semantic_file_out_node.location = (2 * dx + 80, -700)
    _reset_file_output_node(semantic_file_out_node, output_dir)
    _configure_file_output_node_format(
        semantic_file_out_node,
        file_format="PNG",
        color_mode="BW",
        color_depth="16",
    )

    depth_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    depth_file_out_node.location = (2 * dx + 120, -1050)
    _reset_file_output_node(depth_file_out_node, output_dir)
    _configure_file_output_node_format(
        depth_file_out_node,
        file_format="OPEN_EXR",
        color_mode="BW",
        color_depth="32",
    )

    depth_preview_file_out_node = tree.nodes.new(type="CompositorNodeOutputFile")
    depth_preview_file_out_node.location = (2 * dx + 160, -1250)
    _reset_file_output_node(depth_preview_file_out_node, output_dir)
    _configure_file_output_node_format(
        depth_preview_file_out_node,
        file_format="PNG",
        color_mode="BW",
        color_depth="16",
    )

    index_ob = _find_socket_by_name(render_layers.outputs, "Object Index")
    index_ma = _find_socket_by_name(render_layers.outputs, "Material Index")
    index_sockets = [index_ob, index_ma]

    semantic_outputs: dict[str, typing.Any] = {}
    semantic_names = {
        _normalize_socket_name(_semantic_aov_name(channel))
        for channel in (semantic_channels or set())
    }
    depth_preview_connected = False

    for output in render_layers.outputs:
        if output in index_sockets:
            continue

        normalized_name = _normalize_socket_name(output.name)
        if normalized_name in semantic_names:
            semantic_outputs[output.name] = output
            continue

        if normalized_name in {"depth", "z"}:
            depth_slot_name = output.name
            depth_input = _add_file_output_item(
                depth_file_out_node, depth_slot_name, output
            )
            _configure_file_output_item(
                depth_file_out_node,
                depth_slot_name,
                file_path=depth_slot_name,
            )
            tree.links.new(output, depth_input)

            if not depth_preview_connected:
                normalize_node = tree.nodes.new(type="CompositorNodeNormalize")
                normalize_node.location = (dx, -1200)
                normalize_node.hide = True
                tree.links.new(output, normalize_node.inputs[0])

                preview_slot_name = "DepthPreview"
                preview_input = _add_file_output_item(
                    depth_preview_file_out_node,
                    preview_slot_name,
                    normalize_node.outputs[0],
                )
                _configure_file_output_item(
                    depth_preview_file_out_node,
                    preview_slot_name,
                    file_path=preview_slot_name,
                )
                tree.links.new(normalize_node.outputs[0], preview_input)
                depth_preview_connected = True
            continue

        slot_name = output.name
        out_input = _add_file_output_item(file_out_node, slot_name, output)
        _configure_file_output_item(
            file_out_node,
            slot_name,
            file_path=slot_name,
        )
        tree.links.new(output, out_input)

    preview_group = bpy.data.node_groups.get("PreviewIndex")
    for i, index_output in enumerate(index_sockets):
        if index_output is None:
            continue

        divider_node = tree.nodes.new(type="ShaderNodeMath")
        divider_node.operation = "DIVIDE"
        divider_node.inputs[1].default_value = 2**16
        divider_node.location = (dx, -350 - dy * i)
        divider_node.hide = True

        index_name = _index_slot_name(i)
        index_input = _add_file_output_item(
            index_file_out_node, index_name, index_output
        )
        _configure_file_output_item(
            index_file_out_node,
            index_name,
            file_path=index_name,
        )
        tree.links.new(index_output, divider_node.inputs[0])
        tree.links.new(divider_node.outputs[0], index_input)

        if preview_group is not None:
            preview_node = tree.nodes.new(type="CompositorNodeGroup")
            preview_node.node_tree = preview_group
            preview_node.location = (dx, -200 - dy * i)
            preview_node.label = f"{index_name} Preview"
            preview_node.hide = True

            preview_input = _find_socket_by_name(preview_node.inputs, "Index")
            preview_output = _find_socket_by_name(preview_node.outputs, "Preview")
            if preview_input is not None and preview_output is not None:
                preview_name = _preview_slot_name(i)
                preview_file_input = _add_file_output_item(
                    file_out_node, preview_name, preview_output
                )
                _configure_file_output_item(
                    file_out_node,
                    preview_name,
                    file_path=preview_name,
                )
                tree.links.new(index_output, preview_input)
                tree.links.new(preview_output, preview_file_input)

    for socket_name, socket in semantic_outputs.items():
        threshold = tree.nodes.new(type="ShaderNodeMath")
        threshold.operation = "GREATER_THAN"
        threshold.inputs[1].default_value = semantic_mask_threshold
        threshold.location = (dx, -700 - dy)
        threshold.hide = True
        tree.links.new(socket, threshold.inputs[0])

        channel = _normalize_semantic_channel(socket_name)
        mask_slot_name = f"Mask_{channel}"
        sem_input = _add_file_output_item(
            semantic_file_out_node,
            mask_slot_name,
            threshold.outputs[0],
        )
        _configure_file_output_item(
            semantic_file_out_node,
            mask_slot_name,
            file_path=mask_slot_name,
        )
        tree.links.new(threshold.outputs[0], sem_input)


def _get_compositor_tree(scene: bpy.types.Scene):
    tree = scene.compositing_node_group
    if tree is None:
        tree = bpy.data.node_groups.new(
            name=f"RVCompositor_{scene.name}",
            type="CompositorNodeTree",
        )
        _mark_node_tree(tree)
        scene.compositing_node_group = tree
    else:
        _mark_node_tree(tree)
    return tree


def _connect_group_output_image(tree, render_layers, dx: float, dy: float):
    group_output = tree.nodes.new(type="NodeGroupOutput")
    group_output.location = (dx, dy)

    _ensure_group_output_socket(tree, "Image")
    image_input = _find_socket_by_name(group_output.inputs, "Image")
    image_output = _find_socket_by_name(render_layers.outputs, "Image")
    if image_input is None or image_output is None:
        raise RuntimeError("Failed to bind compositor Image output socket.")
    tree.links.new(image_output, image_input)


def _ensure_group_output_socket(tree, socket_name: str):
    target = _normalize_socket_name(socket_name)
    for item in tree.interface.items_tree:
        item_name = getattr(item, "name", None)
        if item_name is not None and _normalize_socket_name(item_name) == target:
            return

    tree.interface.new_socket(
        name=socket_name,
        in_out="OUTPUT",
        socket_type="NodeSocketColor",
    )


def _reset_file_output_node(node, output_dir: str | None):
    node.file_output_items.clear()
    if output_dir is not None:
        node.directory = output_dir
    node.file_name = ""


def _add_file_output_item(node, slot_name: str, source_socket):
    node.file_output_items.new(_socket_type_for_output_item(source_socket), slot_name)
    output_input = _find_socket_by_name(node.inputs, slot_name)
    if output_input is None:
        raise RuntimeError(f"File output socket '{slot_name}' was not created.")
    return output_input


def _configure_file_output_item(
    node,
    slot_name: str,
    file_path: str,
):
    item = _find_file_output_item(node, slot_name)
    if item is None:
        raise RuntimeError(f"File output item '{slot_name}' not found.")

    if hasattr(item, "override_node_format"):
        item.override_node_format = False
    if hasattr(item, "path"):
        item.path = file_path
    if hasattr(item, "name"):
        item.name = file_path


def _configure_file_output_node_format(
    node,
    file_format: str,
    color_mode: str,
    color_depth: str,
):
    if hasattr(node.format, "media_type"):
        node.format.media_type = "IMAGE"
    node.format.file_format = file_format
    node.format.color_mode = color_mode
    node.format.color_depth = color_depth


def _find_file_output_item(node, slot_name: str):
    target = _normalize_socket_name(slot_name)
    for item in node.file_output_items:
        if _normalize_socket_name(item.name) == target:
            return item
    return None


def _socket_type_for_output_item(source_socket) -> str:
    socket_type = str(getattr(source_socket, "type", "RGBA")).upper()
    mapping = {
        "VALUE": "FLOAT",
        "COLOR": "RGBA",
    }
    socket_type = mapping.get(socket_type, socket_type)

    valid = {
        "FLOAT",
        "INT",
        "BOOLEAN",
        "VECTOR",
        "RGBA",
        "ROTATION",
        "MATRIX",
        "STRING",
        "MENU",
        "SHADER",
        "OBJECT",
        "IMAGE",
        "GEOMETRY",
        "COLLECTION",
        "TEXTURE",
        "MATERIAL",
        "BUNDLE",
        "CLOSURE",
    }
    if socket_type not in valid:
        return "RGBA"
    return socket_type


def _index_slot_name(idx: int) -> str:
    return "IndexOB" if idx == 0 else "IndexMA"


def _preview_slot_name(idx: int) -> str:
    return "PreviewIndexOB" if idx == 0 else "PreviewIndexMA"


def _normalize_socket_name(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum())


def _find_socket_by_name(sockets, candidate: str):
    if candidate in sockets:
        return sockets[candidate]

    target = _normalize_socket_name(candidate)
    for socket in sockets:
        if _normalize_socket_name(socket.name) == target:
            return socket
    return None
