import bpy
from typing import Union
from .utils import _require_blender_attr


def _ensure_rigidbody_world() -> None:
    scene = bpy.context.scene
    if scene.rigidbody_world is None:
        bpy.ops.rigidbody.world_add()


def _configure_rigidbody_world(
    settle_frames: int,
    substeps: int,
    time_scale: float,
    solver_iterations: Union[int, None] = None,
    use_split_impulse: Union[bool, None] = None,
    split_impulse_penetration_threshold: Union[float, None] = None,
) -> tuple[int, int]:
    _ensure_rigidbody_world()
    scene = bpy.context.scene
    rbw = scene.rigidbody_world
    if rbw is None:
        raise RuntimeError("Failed to initialize rigid body world.")

    start_frame = int(scene.frame_start)
    frame_count = max(1, int(settle_frames))
    end_frame = start_frame + frame_count - 1
    scene.frame_set(start_frame)
    if hasattr(scene, "sync_mode"):
        scene.sync_mode = "NONE"
    _require_blender_attr(rbw, "time_scale", "rigid body world time_scale")
    rbw.time_scale = float(time_scale)
    _require_blender_attr(rbw, "substeps_per_frame", "rigid body world substeps")
    rbw.substeps_per_frame = max(1, int(substeps))
    _require_blender_attr(
        rbw, "solver_iterations", "rigid body world solver_iterations"
    )
    iterations = (
        max(1, int(substeps) * 2)
        if solver_iterations is None
        else max(1, int(solver_iterations))
    )
    rbw.solver_iterations = iterations
    if use_split_impulse is not None:
        _require_blender_attr(rbw, "use_split_impulse", "rigid body world split impulse")
        rbw.use_split_impulse = bool(use_split_impulse)
    if split_impulse_penetration_threshold is not None:
        _require_blender_attr(
            rbw,
            "split_impulse_penetration_threshold",
            "rigid body world split impulse penetration threshold",
        )
        rbw.split_impulse_penetration_threshold = float(
            split_impulse_penetration_threshold
        )

    cache = getattr(rbw, "point_cache", None)
    if cache is not None:
        cache.frame_start = start_frame
        cache.frame_end = end_frame
    return start_frame, end_frame


def _simulate_rigidbody(
    settle_frames: int,
    substeps: int,
    time_scale: float,
    solver_iterations: Union[int, None] = None,
    use_split_impulse: Union[bool, None] = None,
    split_impulse_penetration_threshold: Union[float, None] = None,
) -> tuple[int, int]:
    start_frame, end_frame = _configure_rigidbody_world(
        settle_frames=settle_frames,
        substeps=substeps,
        time_scale=time_scale,
        solver_iterations=solver_iterations,
        use_split_impulse=use_split_impulse,
        split_impulse_penetration_threshold=split_impulse_penetration_threshold,
    )
    for frame in range(start_frame, end_frame + 1):
        bpy.context.scene.frame_set(frame)
    return start_frame, end_frame


def simulate_physics(
    frames: int = 20,
    substeps: int = 10,
    time_scale: float = 1.0,
    solver_iterations: Union[int, None] = None,
    use_split_impulse: Union[bool, None] = None,
    split_impulse_penetration_threshold: Union[float, None] = None,
) -> None:
    """
    Simulate current Blender rigid-body world for a fixed number of frames.

    Users are expected to explicitly add rigid bodies via `Object.add_rigidbody(...)`
    and then call `rv.simulate_physics(...)` at chosen points in scene generation.
    """
    if frames <= 0:
        raise ValueError("frames must be > 0.")
    if substeps <= 0:
        raise ValueError("substeps must be > 0.")
    if time_scale <= 0:
        raise ValueError("time_scale must be > 0.")
    if solver_iterations is not None and int(solver_iterations) <= 0:
        raise ValueError("solver_iterations must be > 0.")
    if (
        split_impulse_penetration_threshold is not None
        and float(split_impulse_penetration_threshold) < 0
    ):
        raise ValueError("split_impulse_penetration_threshold must be >= 0.")

    _simulate_rigidbody(
        settle_frames=int(frames),
        substeps=int(substeps),
        time_scale=float(time_scale),
        solver_iterations=(
            None if solver_iterations is None else int(solver_iterations)
        ),
        use_split_impulse=use_split_impulse,
        split_impulse_penetration_threshold=(
            None
            if split_impulse_penetration_threshold is None
            else float(split_impulse_penetration_threshold)
        ),
    )
