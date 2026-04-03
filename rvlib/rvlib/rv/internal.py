"""
Runner-only helpers for the `rvlib` runtime.

These functions are intentionally separated from the public `rv` package API.
They remain importable for bundled runners such as preview/render/export.
"""

from .utils import (
    _internal_begin_run,
    _internal_configure_cycles_backend,
    _internal_end_run,
    _internal_iter_cycles_devices,
    _internal_load_scene_class,
    _internal_parse_resolution,
    _internal_print_cycles_device_info,
    _internal_set_time_limit,
)

__all__ = [
    "_internal_begin_run",
    "_internal_configure_cycles_backend",
    "_internal_end_run",
    "_internal_iter_cycles_devices",
    "_internal_load_scene_class",
    "_internal_parse_resolution",
    "_internal_print_cycles_device_info",
    "_internal_set_time_limit",
]


def __getattr__(name: str):
    if name == "_ACTIVE_RUN_ID":
        from . import utils as _utils

        return _utils._ACTIVE_RUN_ID
    raise AttributeError(name)
