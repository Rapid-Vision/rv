import math
import warnings
from mathutils import Vector

from .types import Float2, ObjectLoaderSource, ScatterValidationResult


def _ensure_positive_tuple(values, expected_len: int, name: str) -> None:
    if len(values) != expected_len:
        raise ValueError(f"{name} must contain exactly {expected_len} values.")
    for value in values:
        if float(value) <= 0:
            raise ValueError(f"{name} values must be > 0.")


def _validate_scatter_common(
    source: ObjectLoaderSource,
    count: int,
    domain: "Domain",
    min_gap: float,
    yaw_range: Float2,
    rotation_mode: str,
    scale_range: Float2,
    max_attempts_per_object: int,
    boundary_mode: str,
    boundary_margin: float,
) -> ScatterValidationResult:
    from .scene import Domain
    from .object import ObjectLoader

    if count <= 0:
        raise ValueError("count must be > 0.")
    if not isinstance(domain, Domain):
        raise TypeError("domain must be an instance of Domain.")
    if min_gap < 0:
        raise ValueError("min_gap must be >= 0.")
    if boundary_margin < 0:
        raise ValueError("boundary_margin must be >= 0.")
    if max_attempts_per_object <= 0:
        raise ValueError("max_attempts_per_object must be > 0.")
    if boundary_mode != "center_margin":
        raise ValueError("boundary_mode must be center_margin.")
    if rotation_mode not in {"yaw", "free"}:
        raise ValueError("rotation_mode must be one of: yaw, free.")
    if len(scale_range) != 2:
        raise ValueError("scale_range must contain exactly two values.")
    scale_min = float(scale_range[0])
    scale_max = float(scale_range[1])
    if scale_min <= 0 or scale_max <= 0:
        raise ValueError("scale_range values must be > 0.")
    if scale_min > scale_max:
        raise ValueError("scale_range must satisfy min <= max.")
    if len(yaw_range) != 2:
        raise ValueError("yaw_range must contain exactly two values.")
    yaw_min = float(yaw_range[0])
    yaw_max = float(yaw_range[1])
    if yaw_min > yaw_max:
        raise ValueError("yaw_range must satisfy min <= max.")

    loaders: list[ObjectLoader]
    if isinstance(source, ObjectLoader):
        loaders = [source]
    elif isinstance(source, (list, tuple)) and len(source) > 0:
        if not all(isinstance(loader, ObjectLoader) for loader in source):
            raise TypeError("source sequence must contain only ObjectLoader instances.")
        loaders = list(source)
    else:
        raise TypeError(
            "source must be ObjectLoader or non-empty sequence[ObjectLoader]."
        )

    for loader in loaders:
        if getattr(loader.obj, "data", None) is None:
            raise ValueError("source object must have geometry data.")

    return loaders, scale_min, scale_max, yaw_min, yaw_max


def _init_scatter_stats(
    requested: int, domain_kind: str, strategy: str, seed: int | None
) -> dict:
    return {
        "requested": requested,
        "placed": 0,
        "attempts": 0,
        "rejected_boundary": 0,
        "rejected_overlap": 0,
        "rejected_attempt_limit": 0,
        "strategy": strategy,
        "domain_kind": domain_kind,
        "seed": seed,
    }


def _finalize_scatter_stats(
    scene: "Scene", stats: dict, placed: list["Object"], requested: int
) -> None:
    stats["placed"] = len(placed)
    if len(placed) < requested:
        warnings.warn(
            "scatter placed "
            f"{len(placed)}/{requested} objects after {stats['attempts']} attempts "
            f"(strategy={stats['strategy']}, domain={stats['domain_kind']}, seed={stats['seed']})."
        )

    scatter_runs = scene.custom_meta.get("scatter_runs", [])
    if not isinstance(scatter_runs, list):
        scatter_runs = [scatter_runs]
    scatter_runs.append(stats)
    scene.custom_meta["scatter_runs"] = scatter_runs


def _overlaps_by_radius(
    position: Vector,
    radius: float,
    neighbors: list[int],
    placed_infos: list[dict],
    dimension: int,
    min_gap: float,
) -> bool:
    for neighbor_idx in neighbors:
        neighbor = placed_infos[neighbor_idx]
        if dimension == 2:
            dist = math.hypot(
                position.x - neighbor["position"].x,
                position.y - neighbor["position"].y,
            )
        else:
            dist = (position - neighbor["position"]).length
        if dist + 1e-9 < radius + neighbor["radius"] + min_gap:
            return True
    return False
