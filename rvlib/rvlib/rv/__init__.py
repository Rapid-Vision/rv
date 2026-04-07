"""
Module for describing `rv` scenes.

- Preview a scene with `rv preview <scene.py>`.
- Render a dataset with `rv render <scene.py>`.

User-facing names are listed in `__all__`.
Runner-only helpers remain importable as underscored module attributes for the
`rvlib` runtime, but they are intentionally excluded from `__all__`.
"""

import bpy
import mathutils
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .domain import Domain
from .material import BasicMaterial, ImportedMaterial, Material
from .object import (
    AreaLight,
    Camera,
    Light,
    Object,
    ObjectLoader,
    ObjectStats,
    PointLight,
    SpotLight,
    SunLight,
)
from .passes import PASS_MAP, RenderPass
from .physics import simulate_physics
from .scene import Scene
from .shader import (
    ColorValue,
    NormalMap,
    PrincipledBSDF,
    ShaderMaterial,
    TextureImage,
    Value,
    VectorValue,
)
from .state import __getattr__
from .types import (
    AABB,
    CellCoords,
    Color,
    ColorRGB,
    ColorRGBA,
    Float2,
    Float3,
    Float4,
    JSONSerializable,
    ObjectLoaderSource,
    OptionalColor,
    Polygon2D,
    RenderPassSet,
    Resolution,
    ScatterValidationResult,
    ScatterSource,
    SemanticChannelSet,
    TagSet,
)
from .world import BasicWorld, HDRIWorld, ImportedWorld, SkyWorld, World

__all__ = [
    "AABB",
    "AreaLight",
    "BasicMaterial",
    "BasicWorld",
    "BVHTree",
    "Camera",
    "CellCoords",
    "Color",
    "ColorRGB",
    "ColorRGBA",
    "Domain",
    "Float2",
    "Float3",
    "Float4",
    "HDRIWorld",
    "ImportedMaterial",
    "ImportedWorld",
    "JSONSerializable",
    "Light",
    "Material",
    "Object",
    "ObjectLoader",
    "ObjectLoaderSource",
    "ObjectStats",
    "OptionalColor",
    "PointLight",
    "Polygon2D",
    "PrincipledBSDF",
    "RenderPass",
    "RenderPassSet",
    "Resolution",
    "ScatterValidationResult",
    "ScatterSource",
    "Scene",
    "SemanticChannelSet",
    "ShaderMaterial",
    "SkyWorld",
    "SpotLight",
    "SunLight",
    "TagSet",
    "TextureImage",
    "ColorValue",
    "Value",
    "Vector",
    "VectorValue",
    "World",
    "NormalMap",
    "simulate_physics",
]
