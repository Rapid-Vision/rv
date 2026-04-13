from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class RegressionCase:
    name: str
    script: Path
    cwd: Path
    resolution: tuple[int, int] = (192, 192)
    compare_size: tuple[int, int] = (96, 96)
    image_number: int = 1
    procs: int = 1
    seed: int = 42
    gpu_backend: str = "cpu"
    max_samples: int = 8
    time_limit: float = 30.0
    jpeg_quality: int = 35
    mean_epsilon: float = 12.0
    max_epsilon: int = 64
    args: tuple[str, ...] = field(default_factory=tuple)


def _example_case(example_dir: str, script_name: str) -> RegressionCase:
    script = REPO_ROOT / "examples" / example_dir / script_name
    return RegressionCase(
        name=f"{example_dir.replace('/', '_')}_{script_name.removesuffix('.py')}",
        script=script,
        cwd=script.parent,
    )


CASES: tuple[RegressionCase, ...] = (
    _example_case("1_primitives", "scene.py"),
    _example_case("2_properties", "scene.py"),
    _example_case("3_scattering", "custom_domain.py"),
    _example_case("3_scattering", "ellipse_2d.py"),
    _example_case("3_scattering", "hull_3d.py"),
    _example_case("3_scattering", "parametric_scatter.py"),
    _example_case("4_semantic_aov", "scene.py"),
    _example_case("5_physics", "scatter.py"),
    _example_case("5_physics", "simple.py"),
    _example_case("5_physics", "wall_break.py"),
    _example_case("7_modules", "scene.py"),
    _example_case("8_shader_graph", "scene.py"),
)


def find_cases(selected: set[str] | None = None) -> list[RegressionCase]:
    if not selected:
        return list(CASES)
    return [case for case in CASES if case.name in selected]
