import bpy


def _normalize_modifier_input_name(name: str) -> str:
    return "".join(ch.lower() for ch in name if ch.isalnum())


def _iter_modifier_group_inputs(modifier):
    node_group = getattr(modifier, "node_group", None)
    if node_group is None:
        return []

    interface = getattr(node_group, "interface", None)
    items_tree = getattr(interface, "items_tree", None)
    if items_tree is not None:
        return [
            item
            for item in items_tree
            if getattr(item, "item_type", None) == "SOCKET"
            and getattr(item, "in_out", None) == "INPUT"
        ]

    return list(getattr(node_group, "inputs", []))


def _resolve_modifier_input_key(modifier, input_name: str) -> str:
    sockets = list(_iter_modifier_group_inputs(modifier))
    if not sockets:
        raise ValueError(f"Modifier '{modifier.name}' has no exposed inputs.")

    normalized_target = _normalize_modifier_input_name(input_name)
    modifier_keys = set(modifier.keys())
    matches: list[tuple[int, str, str]] = []

    for index, socket in enumerate(sockets, start=1):
        socket_name = str(getattr(socket, "name", ""))
        socket_identifier = str(getattr(socket, "identifier", ""))
        normalized_candidates = {
            _normalize_modifier_input_name(socket_name),
            _normalize_modifier_input_name(socket_identifier),
        }
        if normalized_target not in normalized_candidates:
            continue

        for candidate_key in (
            socket_identifier,
            f"Socket_{index}",
            f"Input_{index}",
        ):
            if candidate_key and candidate_key in modifier_keys:
                matches.append((index, socket_name, candidate_key))
                break

    if len(matches) == 1:
        return matches[0][2]
    if len(matches) > 1:
        matched = ", ".join(
            f"{socket_name} ({modifier.name})" for _, socket_name, _ in matches
        )
        raise ValueError(
            f"Input '{input_name}' is ambiguous across exposed modifier sockets: {matched}"
        )

    available = ", ".join(
        str(getattr(socket, "name", getattr(socket, "identifier", "")))
        for socket in sockets
    )
    raise ValueError(
        f"Modifier '{modifier.name}' has no input named '{input_name}'. "
        f"Available inputs: [{available}]"
    )


def _resolve_nodes_modifier(
    obj: bpy.types.Object,
    input_name: str | None = None,
    modifier_name: str | None = None,
):
    modifiers = list(getattr(obj, "modifiers", []))
    if modifier_name is not None:
        modifier = obj.modifiers.get(modifier_name)
        if modifier is None:
            available = ", ".join(mod.name for mod in modifiers)
            raise ValueError(
                f"Modifier '{modifier_name}' was not found on object '{obj.name}'. "
                f"Available modifiers: [{available}]"
            )
        if getattr(modifier, "type", None) != "NODES":
            raise ValueError(
                f"Modifier '{modifier_name}' is not a Geometry Nodes modifier."
            )
        return modifier

    nodes_modifiers = [
        modifier for modifier in modifiers if getattr(modifier, "type", None) == "NODES"
    ]
    if not nodes_modifiers:
        raise ValueError(f"Object '{obj.name}' has no Geometry Nodes modifiers.")
    if len(nodes_modifiers) == 1:
        return nodes_modifiers[0]
    if input_name is None:
        available = ", ".join(mod.name for mod in nodes_modifiers)
        raise ValueError(
            f"Object '{obj.name}' has multiple Geometry Nodes modifiers. "
            f"Specify modifier_name. Available modifiers: [{available}]"
        )

    matches = []
    for modifier in nodes_modifiers:
        try:
            _resolve_modifier_input_key(modifier, input_name)
        except ValueError:
            continue
        matches.append(modifier)

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        available = ", ".join(mod.name for mod in matches)
        raise ValueError(
            f"Input '{input_name}' exists on multiple Geometry Nodes modifiers for "
            f"object '{obj.name}'. Specify modifier_name. Matching modifiers: [{available}]"
        )

    available = ", ".join(mod.name for mod in nodes_modifiers)
    raise ValueError(
        f"No Geometry Nodes modifier on object '{obj.name}' exposes input "
        f"'{input_name}'. Available modifiers: [{available}]"
    )
