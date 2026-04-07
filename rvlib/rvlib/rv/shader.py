from dataclasses import dataclass, fields, is_dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

import bpy

from .material import Material
from .utils import _as_rgba

X_SHIFT = 300
Y_PADDING = 60
def _coerce_expr(value: "ShaderValueLike", expected_type: str | None = None) -> "Expr":
    if isinstance(value, Expr):
        return value
    if isinstance(value, (int, float)):
        scalar = float(value)
        if expected_type == "RGBA":
            return ColorValue((scalar, scalar, scalar, 1.0))
        if expected_type == "VECTOR":
            return VectorValue((scalar, scalar, scalar))
        return Value(scalar)
    if isinstance(value, (tuple, list)):
        if expected_type == "VALUE":
            raise TypeError("Scalar shader inputs do not accept tuple values.")
        if expected_type == "VECTOR":
            return VectorValue(tuple(float(component) for component in value))
        return ColorValue(tuple(float(component) for component in value))
    raise TypeError(f"Unsupported shader value: {value!r}")


class Expr:
    value_type: str

    def _child_exprs(self) -> tuple["Expr", ...]:
        return ()

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        raise TypeError(f"Unsupported shader expression: {self!r}")

    def node_height(self) -> int:
        return 180

    def to_meta(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"type": self.__class__.__name__}
        if is_dataclass(self):
            for field in fields(self):
                payload[field.name] = _serialize_shader_meta(getattr(self, field.name))
        return payload

    @cached_property
    def x_depth(self) -> int:
        children = self._child_exprs()
        if not children:
            return 0
        return max(child.x_depth for child in children) + 1

    def __add__(self, other: "ShaderValueLike") -> "Expr":
        return BinaryMath(
            "ADD", self, _coerce_expr(other, expected_type=self.value_type)
        )

    def __radd__(self, other: "ShaderValueLike") -> "Expr":
        return _coerce_expr(other, expected_type=self.value_type).__add__(self)

    def __sub__(self, other: "ShaderValueLike") -> "Expr":
        return BinaryMath(
            "SUBTRACT", self, _coerce_expr(other, expected_type=self.value_type)
        )

    def __rsub__(self, other: "ShaderValueLike") -> "Expr":
        return _coerce_expr(other, expected_type=self.value_type).__sub__(self)

    def __mul__(self, other: "ShaderValueLike") -> "Expr":
        return BinaryMath(
            "MULTIPLY", self, _coerce_expr(other, expected_type=self.value_type)
        )

    def __rmul__(self, other: "ShaderValueLike") -> "Expr":
        return _coerce_expr(other, expected_type=self.value_type).__mul__(self)

    def __truediv__(self, other: "ShaderValueLike") -> "Expr":
        return BinaryMath(
            "DIVIDE", self, _coerce_expr(other, expected_type=self.value_type)
        )

    def __rtruediv__(self, other: "ShaderValueLike") -> "Expr":
        return _coerce_expr(other, expected_type=self.value_type).__truediv__(self)


class FloatExpr(Expr):
    value_type = "VALUE"


class ColorExpr(Expr):
    value_type = "RGBA"


class VectorExpr(Expr):
    value_type = "VECTOR"


class NormalExpr(VectorExpr):
    pass


class ShaderExpr(Expr):
    value_type = "SHADER"


ShaderValueLike = Expr | int | float | tuple[float, ...] | list[float]


def _serialize_shader_meta(value: Any) -> Any:
    if isinstance(value, Expr):
        return value.to_meta()
    if isinstance(value, tuple):
        return [_serialize_shader_meta(item) for item in value]
    if isinstance(value, list):
        return [_serialize_shader_meta(item) for item in value]
    if isinstance(value, dict):
        return {key: _serialize_shader_meta(item) for key, item in value.items()}
    return value


@dataclass(frozen=True)
class Value(FloatExpr):
    value: float

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeValue", self)
        node.outputs[0].default_value = self.value
        return node.outputs[0]

    def node_height(self) -> int:
        return 120


@dataclass(frozen=True)
class ColorValue(ColorExpr):
    value: tuple[float, ...]

    def __post_init__(self):
        object.__setattr__(self, "value", _as_rgba(self.value))

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeRGB", self)
        node.outputs[0].default_value = self.value
        return node.outputs[0]

    def node_height(self) -> int:
        return 140


@dataclass(frozen=True)
class VectorValue(VectorExpr):
    value: tuple[float, ...]

    def __post_init__(self):
        vector = tuple(float(component) for component in self.value)
        if len(vector) != 3:
            raise TypeError("Vector must have exactly 3 components.")
        object.__setattr__(self, "value", vector)

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeCombineXYZ", self)
        node.inputs[0].default_value = self.value[0]
        node.inputs[1].default_value = self.value[1]
        node.inputs[2].default_value = self.value[2]
        return node.outputs[0]

    def node_height(self) -> int:
        return 180


@dataclass(frozen=True)
class BinaryMath(Expr):
    operation: str
    left: Expr
    right: Expr

    @property
    def value_type(self) -> str:
        if self.left.value_type != self.right.value_type:
            raise TypeError(
                f"Incompatible shader math types: {self.left.value_type} and {self.right.value_type}."
            )
        if self.left.value_type == "SHADER":
            raise TypeError("Shader sockets do not support arithmetic.")
        return self.left.value_type

    def _child_exprs(self) -> tuple[Expr, ...]:
        return (self.left, self.right)

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        if self.value_type == "VALUE":
            node = compiler.new_node("ShaderNodeMath", self)
            node.operation = self.operation
            compiler.link(self.left, node.inputs[0])
            compiler.link(self.right, node.inputs[1])
            return node.outputs[0]
        if self.value_type == "RGBA":
            node = compiler.new_node("ShaderNodeMix", self)
            node.data_type = "RGBA"
            node.blend_type = self.operation
            node.inputs["Factor"].default_value = 1.0
            compiler.link(self.left, node.inputs["A"])
            compiler.link(self.right, node.inputs["B"])
            return node.outputs["Result"]
        if self.value_type == "VECTOR":
            node = compiler.new_node("ShaderNodeVectorMath", self)
            node.operation = self.operation
            compiler.link(self.left, node.inputs[0])
            compiler.link(self.right, node.inputs[1])
            return node.outputs[0]
        raise TypeError(f"Unsupported shader math type: {self.value_type}.")

    def node_height(self) -> int:
        if self.value_type == "RGBA":
            return 220
        if self.value_type == "VECTOR":
            return 200
        return 160


@dataclass(frozen=True)
class TextureImage(ColorExpr):
    path: str
    colorspace: str = "sRGB"
    interpolation: str = "Linear"
    projection: str = "FLAT"

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeTexImage", self)
        path = str(Path(self.path).expanduser().resolve())
        node.image = compiler.load_image(path, self.colorspace)
        node.interpolation = self.interpolation
        node.projection = self.projection
        return node.outputs["Color"]

    def node_height(self) -> int:
        return 320


@dataclass(frozen=True)
class NormalMap(NormalExpr):
    color: ShaderValueLike
    strength: ShaderValueLike = 1.0
    space: str = "TANGENT"

    def __post_init__(self):
        object.__setattr__(
            self, "color", _coerce_expr(self.color, expected_type="RGBA")
        )
        object.__setattr__(
            self, "strength", _coerce_expr(self.strength, expected_type="VALUE")
        )

    def _child_exprs(self) -> tuple[Expr, ...]:
        return (self.color, self.strength)

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeNormalMap", self)
        node.space = self.space
        compiler.link(self.color, node.inputs["Color"])
        compiler.link(self.strength, node.inputs["Strength"])
        return node.outputs["Normal"]

    def node_height(self) -> int:
        return 180


@dataclass(frozen=True)
class PrincipledBSDF(ShaderExpr):
    base_color: ShaderValueLike | None = None
    metallic: ShaderValueLike | None = None
    roughness: ShaderValueLike | None = None
    specular: ShaderValueLike | None = None
    normal: ShaderValueLike | None = None
    emission_color: ShaderValueLike | None = None
    emission_strength: ShaderValueLike | None = None
    alpha: ShaderValueLike | None = None
    transmission: ShaderValueLike | None = None
    ior: ShaderValueLike | None = None

    def __post_init__(self):
        for field_name, socket_type in (
            ("base_color", "RGBA"),
            ("metallic", "VALUE"),
            ("roughness", "VALUE"),
            ("specular", "VALUE"),
            ("normal", "VECTOR"),
            ("emission_color", "RGBA"),
            ("emission_strength", "VALUE"),
            ("alpha", "VALUE"),
            ("transmission", "VALUE"),
            ("ior", "VALUE"),
        ):
            value = getattr(self, field_name)
            if value is not None:
                object.__setattr__(
                    self,
                    field_name,
                    _coerce_expr(value, expected_type=socket_type),
                )

    def _child_exprs(self) -> tuple[Expr, ...]:
        children: list[Expr] = []
        for field_name in (
            "base_color",
            "metallic",
            "roughness",
            "specular",
            "normal",
            "emission_color",
            "emission_strength",
            "alpha",
            "transmission",
            "ior",
        ):
            value = getattr(self, field_name)
            if value is not None:
                children.append(value)
        return tuple(children)

    def compile(self, compiler: "_ShaderGraphCompiler") -> bpy.types.NodeSocket:
        node = compiler.new_node("ShaderNodeBsdfPrincipled", self)
        compiler.connect_optional(node.inputs["Base Color"], self.base_color)
        compiler.connect_optional(node.inputs["Metallic"], self.metallic)
        compiler.connect_optional(node.inputs["Roughness"], self.roughness)
        compiler.connect_optional(node.inputs["Specular IOR Level"], self.specular)
        compiler.connect_optional(node.inputs["Normal"], self.normal)
        compiler.connect_optional(node.inputs["Emission Color"], self.emission_color)
        compiler.connect_optional(
            node.inputs["Emission Strength"], self.emission_strength
        )
        compiler.connect_optional(node.inputs["Alpha"], self.alpha)
        compiler.connect_optional(
            node.inputs["Transmission Weight"], self.transmission
        )
        compiler.connect_optional(node.inputs["IOR"], self.ior)
        return node.outputs["BSDF"]

    def node_height(self) -> int:
        return 420


class ShaderMaterial(Material):
    shader: ShaderExpr
    properties: dict[str, Any]

    def __init__(self, shader: ShaderExpr, name: str = "Material"):
        super().__init__(name=name)
        self.shader = shader
        self.properties = {}

    def set_params(self, shader: ShaderExpr | None = None):
        if shader is not None:
            self.shader = shader
        return self

    def set_property(self, key: str, value: Any):
        self.properties[key] = value
        return self

    def _build_material(self) -> bpy.types.Material:
        material = bpy.data.materials.new(name=self.name or "Material")
        material.use_nodes = True
        node_tree = material.node_tree
        if node_tree is None:
            raise RuntimeError("Material node tree is not available.")

        node_tree.nodes.clear()
        compiler = _ShaderGraphCompiler(node_tree)
        shader_socket = compiler.compile(self.shader)

        output = node_tree.nodes.new(type="ShaderNodeOutputMaterial")
        output.location = ((self.shader.x_depth + 1) * X_SHIFT, 0)
        node_tree.links.new(shader_socket, output.inputs["Surface"])

        alpha_expr = getattr(self.shader, "alpha", None)
        if alpha_expr is not None and not (
            isinstance(alpha_expr, Value) and alpha_expr.value >= 1.0
        ):
            material.blend_method = "BLEND"

        for key, value in self.properties.items():
            material[key] = value

        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "shader": self.shader.to_meta(),
                "properties": self.properties,
            }
        )
        return res


class _ShaderGraphCompiler:
    def __init__(self, node_tree: bpy.types.NodeTree):
        self.node_tree = node_tree
        self._cache: dict[Expr, bpy.types.NodeSocket] = {}
        self._column_heights: dict[int, int] = {}
        self._image_cache: dict[tuple[str, str], bpy.types.Image] = {}

    def compile(self, expr: Expr) -> bpy.types.NodeSocket:
        cached = self._cache.get(expr)
        if cached is not None:
            return cached

        socket = expr.compile(self)
        self._cache[expr] = socket
        return socket

    def new_node(self, node_type: str, expr: Expr) -> bpy.types.Node:
        node = self.node_tree.nodes.new(type=node_type)
        self._place_node(node, expr)
        return node

    def link(self, expr: Expr, socket: bpy.types.NodeSocket) -> None:
        self.node_tree.links.new(self.compile(expr), socket)

    def connect_optional(self, socket: bpy.types.NodeSocket, expr: Expr | None) -> None:
        if expr is None:
            return
        self.link(expr, socket)

    def _place_node(self, node: bpy.types.Node, expr: Expr) -> None:
        x_depth = expr.x_depth
        column_height = self._column_heights.get(x_depth, 0)
        node.location = (x_depth * X_SHIFT, -column_height)
        self._column_heights[x_depth] = column_height + expr.node_height() + Y_PADDING

    def load_image(self, path: str, colorspace: str) -> bpy.types.Image:
        cache_key = (path, colorspace)
        cached = self._image_cache.get(cache_key)
        if cached is not None:
            return cached

        for image in bpy.data.images:
            if bpy.path.abspath(image.filepath) != path:
                continue
            image_colorspace = getattr(image.colorspace_settings, "name", None)
            if image_colorspace == colorspace:
                self._image_cache[cache_key] = image
                return image

        image = bpy.data.images.load(path, check_existing=True)
        image_colorspace = getattr(image.colorspace_settings, "name", None)
        if image_colorspace != colorspace:
            image = image.copy()
            image.filepath = path
            if getattr(image, "colorspace_settings", None) is not None:
                image.colorspace_settings.name = colorspace

        self._image_cache[cache_key] = image
        return image
