from mathutils import Vector
from typing import TypeAlias, Union


JSONSerializable: TypeAlias = Union[
    str, int, float, bool, None, list["JSONSerializable"], dict[str, "JSONSerializable"]
]

Resolution: TypeAlias = tuple[int, int]
Float2: TypeAlias = tuple[float, float]
Float3: TypeAlias = tuple[float, float, float]
Float4: TypeAlias = tuple[float, float, float, float]
ColorRGB: TypeAlias = Float3
ColorRGBA: TypeAlias = Float4
Color: TypeAlias = ColorRGB | ColorRGBA
OptionalColor: TypeAlias = Color | None
Polygon2D: TypeAlias = list[Float2]
AABB: TypeAlias = tuple[Vector, Vector]
CellCoords: TypeAlias = tuple[int, ...]
RenderPassSet: TypeAlias = set["RenderPass"]
TagSet: TypeAlias = set[str]
SemanticChannelSet: TypeAlias = set[str]
ObjectLoaderSource: TypeAlias = Union[
    "ObjectLoader", list["ObjectLoader"], tuple["ObjectLoader", ...]
]
ScatterValidationResult: TypeAlias = tuple[
    list["ObjectLoader"], float, float, float, float
]
