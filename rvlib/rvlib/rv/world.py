from abc import ABC, abstractmethod

import bpy

from .types import ColorRGBA
from .utils import _mark_owned, _mark_world_tree


class World(ABC):
    """
    Base class representing world (environment ligthing).
    """

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def _internal_post_gen(self):
        pass

    @abstractmethod
    def set_params(self):
        """
        Update world-specific lighting parameters.
        """
        pass


class BasicWorld(World):
    """
    `World` class representing a single color environmental lighting.
    """

    color: ColorRGBA | None = None
    strength: float = None

    def __init__(self):
        pass

    def _internal_post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        node_background = nodes.new(type="ShaderNodeBackground")
        node_output = nodes.new(type="ShaderNodeOutputWorld")

        node_background.location = (0, 0)
        node_output.location = (200, 0)
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.color is not None:
            node_background.inputs["Color"].default_value = self.color
        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength

    def set_params(self, color: ColorRGBA | None = None, strength: float = None):
        if color is not None:
            self.color = color
        if strength is not None:
            self.strength = strength


class SkyWorld(World):
    """
    `World` class representing a procedural sky environement.

    For more information, view [official blender docs](https://docs.blender.org/manual/en/latest/render/shader_nodes/textures/sky.html).
    """

    strength: float = None
    sun_size: float = None
    sun_intensity: float = None
    sun_elevation: float = None
    rotation_z: float = None
    altitude: float = None
    air: float = 0.1
    aerosol_density: float = 0.01
    ozone: float = 10.0

    def __init__(self):
        pass

    def _internal_post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        node_background = nodes.new(type="ShaderNodeBackground")
        node_sky_tex = nodes.new(type="ShaderNodeTexSky")
        node_output = nodes.new(type="ShaderNodeOutputWorld")

        node_sky_tex.location = (-300, 0)
        node_background.location = (0, 0)
        node_output.location = (200, 0)

        links.new(node_sky_tex.outputs["Color"], node_background.inputs["Color"])
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength
        if self.sun_size is not None:
            node_sky_tex.sun_size = self.sun_size
        if self.sun_intensity is not None:
            node_sky_tex.sun_intensity = self.sun_intensity
        if self.sun_elevation is not None:
            node_sky_tex.sun_elevation = self.sun_elevation
        if self.rotation_z is not None:
            node_sky_tex.sun_rotation = self.rotation_z
        if self.altitude is not None:
            node_sky_tex.altitude = self.altitude
        if self.air is not None:
            node_sky_tex.air_density = self.air
        if self.aerosol_density is not None:
            node_sky_tex.aerosol_density = self.aerosol_density
        if self.ozone is not None:
            node_sky_tex.ozone_density = self.ozone

    def set_params(
        self,
        strength: float = None,
        sun_size: float = None,
        sun_intensity: float = None,
        sun_elevation: float = None,
        rotation_z: float = None,
        air: float = None,
        aerosol_density: float = None,
        ozone: float = None,
    ):
        if strength is not None:
            self.strength = strength
        if sun_size is not None:
            self.sun_size = sun_size
        if sun_intensity is not None:
            self.sun_intensity = sun_intensity
        if sun_elevation is not None:
            self.sun_elevation = sun_elevation
        if rotation_z is not None:
            self.rotation_z = rotation_z
        if air is not None:
            self.air = air
        if aerosol_density is not None:
            self.aerosol_density = aerosol_density
        if ozone is not None:
            self.ozone = ozone


class HDRIWorld(World):
    """
    `World` class for importing lighting from an hdri `.exr` file.
    """

    hdri_path: str
    strength: float = None
    rotation_z: float = None

    def __init__(self, hdri_path: str):
        self.hdri_path = hdri_path

    def _internal_post_gen(self):
        world = bpy.context.scene.world
        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links
        nodes.clear()

        node_background = nodes.new(type="ShaderNodeBackground")
        node_env_tex = nodes.new(type="ShaderNodeTexEnvironment")
        node_output = nodes.new(type="ShaderNodeOutputWorld")
        node_mapping = nodes.new(type="ShaderNodeMapping")
        node_coord = nodes.new(type="ShaderNodeTexCoord")

        node_coord.location = (-700, 0)
        node_mapping.location = (-500, 0)
        node_env_tex.location = (-300, 0)
        node_background.location = (0, 0)
        node_output.location = (200, 0)

        links.new(node_coord.outputs["Generated"], node_mapping.inputs["Vector"])
        links.new(node_mapping.outputs["Vector"], node_env_tex.inputs["Vector"])
        links.new(node_env_tex.outputs["Color"], node_background.inputs["Color"])
        links.new(node_background.outputs["Background"], node_output.inputs["Surface"])

        if self.hdri_path is not None:
            node_env_tex.image = bpy.data.images.load(
                self.hdri_path, check_existing=False
            )
            _mark_owned(node_env_tex.image)

        if self.strength is not None:
            node_background.inputs["Strength"].default_value = self.strength
        if self.rotation_z is not None:
            node_mapping.inputs["Rotation"].default_value[2] = self.rotation_z

    def set_params(
        self,
        hdri_path: str = None,
        strength: float = None,
        rotation_z: float = None,
    ):
        if hdri_path is not None:
            self.hdri_path = hdri_path
        if strength is not None:
            self.strength = strength
        if rotation_z is not None:
            self.rotation_z = rotation_z


class ImportedWorld(World):
    """
    `World` class for importing environment lighting from a `.blend` file.
    """

    filepath: str
    world_name: str = None
    params: dict

    def __init__(self, filepath: str, world_name: str = None):
        self.filepath = filepath
        self.world_name = world_name
        self.params = dict()

    def _internal_post_gen(self):
        with bpy.data.libraries.load(self.filepath, link=False) as (data_from, data_to):
            if self.world_name is None:
                data_to.worlds = [data_from.worlds[0]]
            else:
                data_to.worlds = [self.world_name]
        imported_world = data_to.worlds[0]
        _mark_world_tree(imported_world)
        bpy.context.scene.world = imported_world

        for k, v in self.params.items():
            bpy.context.scene.world[k] = v

    def set_params(self, **kwargs):
        self.params.update(kwargs)
