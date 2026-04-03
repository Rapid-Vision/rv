"""
Module for describing an `rv` scenes. To create a scene implement a class derrived from `Scene`.

- To preview scene use the `rv preview <scene.py>` command.
- To render resulting dataset use the `rv render <scene.py>` command.

View https://rapid-vision.github.io/rv for documentation.
"""

from abc import ABC, abstractmethod
import bmesh
import bpy
import bpy_extras
import json
import math
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import mathutils
import numbers
import os
import pathlib
import random
import typing
from typing import Literal, Optional, Union
import warnings

from .assets import (
    _clear_scene,
    _combine_arglist_set,
    _estimate_loader_radius,
    _load_all_objects,
    _load_single_object,
    _read_json_property,
    _remove_blender_object,
    _restore_modifier_parameters,
    _restore_rv_export_object_metadata,
)
from .compositor import (
    _configure_compositor,
    _configure_semantic_aovs,
    _normalize_socket_name,
)
from .domain import Domain
from .geometry import (
    _aabb_from_points,
    _build_bvh_from_object,
    _convex_hull_2d,
    _convex_hull_planes,
    _cross_2d,
    _distance_point_segment_2d,
    _distance_to_polygon_edges,
    _get_object_local_vertices,
    _get_object_world_location,
    _get_object_world_vertices,
    _mesh_object_overlaps_any,
    _mesh_overlaps_any,
    _object_world_radius,
    _point_in_convex_polygon,
    _points_centroid,
    _polygon_signed_area,
    _random_unit_vector,
    _sample_convex_polygon,
    _sample_rotation_quaternion,
)
from .material import (
    BasicMaterial,
    ImportedMaterial,
    Material,
    _get_principled_bsdf_node,
    _normalize_semantic_channel,
    _semantic_aov_name,
)
from .modifiers import (
    _iter_modifier_group_inputs,
    _normalize_modifier_input_name,
    _resolve_modifier_input_key,
    _resolve_nodes_modifier,
)
from .object import (
    AreaLight,
    Camera,
    Light,
    Object,
    ObjectLoader,
    ObjectStats,
    ParametricSource,
    PointLight,
    SpotLight,
    SunLight,
    _Serializable,
)
from .passes import PASS_MAP, RenderPass
from .physics import (
    _configure_rigidbody_world,
    _ensure_rigidbody_world,
    _simulate_rigidbody,
    simulate_physics,
)
from .render import (
    _configure_passes,
    _deselect,
    _set_resolution,
    _set_time_limit,
    _use_cycles,
    _use_gpu,
)
from .scatter import (
    _ensure_positive_tuple,
    _finalize_scatter_stats,
    _init_scatter_stats,
    _overlaps_by_radius,
    _validate_scatter_common,
)
from .scene import Scene
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
    SemanticChannelSet,
    TagSet,
)
from .utils import (
    _get_generated_collection,
    _internal_begin_run,
    _internal_end_run,
    _is_owned,
    _mark_material_tree,
    _mark_node_tree,
    _mark_object_tree,
    _mark_owned,
    _mark_world_tree,
    _move_object_to_generated_collection,
    _purge_orphans,
    _remove_owned_unused,
    _remove_rv_data,
    _require_blender_attr,
)
from .world import BasicWorld, HDRIWorld, ImportedWorld, SkyWorld, World
