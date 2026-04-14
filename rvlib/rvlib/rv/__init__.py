"""
Package for describing `rv` scenes.

- Preview a scene with `rv preview <scene.py>`.
- Render a dataset with `rv render <scene.py>`.

"""

import bpy
import mathutils
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from .domain import Domain
from .generators import GeneratorFactory, GeneratorHandle
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
from .scene import AssetFactory, LightFactory, MaterialFactory, ObjectFactory, Scene
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
    "AssetFactory",
    "BasicMaterial",
    "BasicWorld",
    "BVHTree",
    "Camera",
    "CellCoords",
    "Color",
    "ColorRGB",
    "ColorRGBA",
    "Domain",
    "GeneratorFactory",
    "GeneratorHandle",
    "Float2",
    "Float3",
    "Float4",
    "HDRIWorld",
    "ImportedMaterial",
    "ImportedWorld",
    "JSONSerializable",
    "Light",
    "LightFactory",
    "Material",
    "MaterialFactory",
    "Object",
    "ObjectFactory",
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
