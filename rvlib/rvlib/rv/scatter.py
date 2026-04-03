import math
import warnings
from mathutils import Vector

from .types import Float2, ScatterSource, ScatterValidationResult


def _ensure_positive_tuple(values, expected_len: int, name: str) -> None:
    if len(values) != expected_len:
        raise ValueError(f"{name} must contain exactly {expected_len} values.")
    for value in values:
        if float(value) <= 0:
            raise ValueError(f"{name} values must be > 0.")


def _normalize_scatter_source(
    source: ScatterSource,
) -> list["ObjectLoader"]:
    from .object import Object, ObjectLoader

    if isinstance(source, Object):
        return [source.as_loader()]
    if isinstance(source, ObjectLoader):
        return [source]
    if isinstance(source, (list, tuple)) and len(source) > 0:
        loaders: list[ObjectLoader] = []
        for item in source:
            if isinstance(item, Object):
                loaders.append(item.as_loader())
            elif isinstance(item, ObjectLoader):
                loaders.append(item)
            else:
                raise TypeError(
                    "source sequence must contain only Object or ObjectLoader instances."
                )
        return loaders
    raise TypeError(
        "source must be Object, ObjectLoader, or non-empty sequence of them."
    )


def _normalize_scatter_scale(scale: float | Float2) -> Float2:
    if isinstance(scale, (int, float)) and not isinstance(scale, bool):
        value = float(scale)
        if value <= 0:
            raise ValueError("scale must be > 0.")
        return (value, value)
    if len(scale) != 2:
        raise ValueError("scale must be a positive number or contain exactly two values.")
    scale_min = float(scale[0])
    scale_max = float(scale[1])
    if scale_min <= 0 or scale_max <= 0:
        raise ValueError("scale values must be > 0.")
    if scale_min > scale_max:
        raise ValueError("scale must satisfy min <= max.")
    return (scale_min, scale_max)


def _normalize_scatter_method(
    method: str,
    domain: "Domain",
    rotation: str,
) -> str:
    if method not in {"auto", "fast", "exact"}:
        raise ValueError("method must be one of: auto, fast, exact.")
    if method != "auto":
        return method
    if domain.dimension == 2 and rotation == "yaw":
        return "fast"
    return "exact"


def _validate_scatter_common(
    source: ScatterSource,
    count: int,
    domain: "Domain",
    gap: float,
    yaw: Float2,
    rotation: str,
    scale: float | Float2,
    max_attempts_per_object: int,
    margin: float,
) -> ScatterValidationResult:
    from .domain import Domain

    if count <= 0:
        raise ValueError("count must be > 0.")
    if not isinstance(domain, Domain):
        raise TypeError("domain must be an instance of Domain.")
    if gap < 0:
        raise ValueError("gap must be >= 0.")
    if margin < 0:
        raise ValueError("margin must be >= 0.")
    if max_attempts_per_object <= 0:
        raise ValueError("max_attempts_per_object must be > 0.")
    if rotation not in {"yaw", "free"}:
        raise ValueError("rotation must be one of: yaw, free.")
    scale_min, scale_max = _normalize_scatter_scale(scale)
    if len(yaw) != 2:
        raise ValueError("yaw must contain exactly two values.")
    yaw_min = float(yaw[0])
    yaw_max = float(yaw[1])
    if yaw_min > yaw_max:
        raise ValueError("yaw must satisfy min <= max.")

    loaders = _normalize_scatter_source(source)

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
