from typing import TYPE_CHECKING, TypeAlias, Union

from mathutils import Vector

if TYPE_CHECKING:
    from .object import Object, ObjectLoader
    from .passes import RenderPass


JSONSerializable: TypeAlias = Union[
    str, int, float, bool, None, list["JSONSerializable"], dict[str, "JSONSerializable"]
]

Resolution: TypeAlias = tuple[int, int]
Float2: TypeAlias = tuple[float, float]
Float3: TypeAlias = tuple[float, float, float]
Float4: TypeAlias = tuple[float, float, float, float]
ColorRGB: TypeAlias = Float3
ColorRGBA: TypeAlias = Float4
Color: TypeAlias = Union[ColorRGB, ColorRGBA]
OptionalColor: TypeAlias = Union[Color, None]
Polygon2D: TypeAlias = list[Float2]
AABB: TypeAlias = tuple[Vector, Vector]
CellCoords: TypeAlias = tuple[int, ...]
RenderPassSet: TypeAlias = set["RenderPass"]
TagSet: TypeAlias = set[str]
SemanticChannelSet: TypeAlias = set[str]
ObjectLoaderSource: TypeAlias = Union[
    "ObjectLoader", list["ObjectLoader"], tuple["ObjectLoader", ...]
]
ScatterSource: TypeAlias = Union[
    "Object",
    "ObjectLoader",
    list[Union["Object", "ObjectLoader"]],
    tuple[Union["Object", "ObjectLoader"], ...],
]
ScatterValidationResult: TypeAlias = tuple[
    list["ObjectLoader"], float, float, float, float
]
