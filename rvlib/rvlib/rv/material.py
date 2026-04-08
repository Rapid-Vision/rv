from abc import ABC, abstractmethod
from typing import Any, Self

import bpy

from .object import _Serializable
from .types import ColorRGBA, OptionalColor
from .utils import _as_rgba, _mark_material_tree


class Material(ABC, _Serializable):
    """
    Base class for material descriptors.

    A material descriptor is converted to a real Blender material when assigned to an object.
    """

    name: str | None
    index: int | None
    _resolved_material: bpy.types.Material | None

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self.name = name
        self.index = None
        self._resolved_material = None

    @abstractmethod
    def set_params(self, **kwargs) -> Self:
        pass

    @abstractmethod
    def _build_material(self) -> bpy.types.Material:
        pass

    def _resolve(self, scene: "Scene") -> bpy.types.Material:
        if self._resolved_material is not None:
            try:
                resolved_name = self._resolved_material.name
                if bpy.data.materials.get(resolved_name) == self._resolved_material:
                    return self._resolved_material
            except Exception:
                pass
            self._resolved_material = None

        material = self._build_material()
        _mark_material_tree(material)
        self.index = scene._register_material(self)
        material.pass_index = self.index
        self._resolved_material = material
        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "type": self.__class__.__name__,
                "index": self.index,
                "name": (
                    self._resolved_material.name
                    if self._resolved_material is not None
                    else self.name
                ),
            }
        )
        return res
def _normalize_semantic_channel(channel: str) -> str:
    normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in channel).strip(
        "_"
    )
    if normalized == "":
        raise ValueError(
            "semantic channel must contain at least one alphanumeric char."
        )
    return normalized


def _semantic_aov_name(channel: str) -> str:
    return _normalize_semantic_channel(channel)


class BasicMaterial(Material):
    """
    Material descriptor backed by Blender's Principled BSDF shader.
    """

    base_color: ColorRGBA | None
    roughness: float | None
    metallic: float | None
    specular: float | None
    emission_color: ColorRGBA | None
    emission_strength: float | None
    alpha: float | None
    transmission: float | None
    ior: float | None
    properties: dict

    def __init__(self, name: str = "Material"):
        super().__init__(name=name)
        self.base_color = None
        self.roughness = None
        self.metallic = None
        self.specular = None
        self.emission_color = None
        self.emission_strength = None
        self.alpha = None
        self.transmission = None
        self.ior = None
        self.properties = dict()

    def set_params(
        self,
        base_color: OptionalColor = None,
        roughness: float | None = None,
        metallic: float | None = None,
        specular: float | None = None,
        emission_color: OptionalColor = None,
        emission_strength: float | None = None,
        alpha: float | None = None,
        transmission: float | None = None,
        ior: float | None = None,
    ):
        if base_color is not None:
            self.base_color = _as_rgba(base_color)
        if roughness is not None:
            self.roughness = roughness
        if metallic is not None:
            self.metallic = metallic
        if specular is not None:
            self.specular = specular
        if emission_color is not None:
            self.emission_color = _as_rgba(emission_color)
        if emission_strength is not None:
            self.emission_strength = emission_strength
        if alpha is not None:
            self.alpha = alpha
        if transmission is not None:
            self.transmission = transmission
        if ior is not None:
            self.ior = ior
        return self

    def set_property(self, key: str, value: Any):
        self.properties[key] = value
        return self

    def _to_shader_material(self) -> "Material":
        from .shader import PrincipledBSDF, ShaderMaterial

        shader = PrincipledBSDF(
            base_color=self.base_color,
            roughness=self.roughness,
            metallic=self.metallic,
            specular=self.specular,
            emission_color=self.emission_color,
            emission_strength=self.emission_strength,
            alpha=self.alpha,
            transmission=self.transmission,
            ior=self.ior,
        )
        material = ShaderMaterial(shader, name=self.name or "Material")
        material.properties.update(self.properties)
        return material

    def _build_material(self) -> bpy.types.Material:
        return self._to_shader_material()._build_material()

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "params": {
                    "base_color": self.base_color,
                    "roughness": self.roughness,
                    "metallic": self.metallic,
                    "specular": self.specular,
                    "emission_color": self.emission_color,
                    "emission_strength": self.emission_strength,
                    "alpha": self.alpha,
                    "transmission": self.transmission,
                    "ior": self.ior,
                },
                "properties": self.properties,
            }
        )
        return res


class ImportedMaterial(Material):
    """
    Material descriptor that imports a material from another `.blend` file.
    """

    filepath: str
    material_name: str | None
    params: dict

    def __init__(self, filepath: str, material_name: str | None = None):
        super().__init__(name=material_name)
        self.filepath = filepath
        self.material_name = material_name
        self.params = dict()

    def set_params(self, **kwargs):
        self.params.update(kwargs)
        return self

    def _build_material(self) -> bpy.types.Material:
        with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
            if self.material_name is None:
                if len(data_from.materials) == 0:
                    raise ValueError(f"No materials found in '{self.filepath}'.")
                data_to.materials = [data_from.materials[0]]
            else:
                if self.material_name not in data_from.materials:
                    available = ", ".join(data_from.materials)
                    raise ValueError(
                        f"Material '{self.material_name}' was not found in '{self.filepath}'. "
                        f"Available materials: [{available}]"
                    )
                data_to.materials = [self.material_name]

        material = data_to.materials[0]
        for key, value in self.params.items():
            material[key] = value
        return material

    def _get_meta(self) -> dict:
        res = super()._get_meta()
        res.update(
            {
                "filepath": self.filepath,
                "material_name": self.material_name,
                "params": self.params,
            }
        )
        return res
