import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")

import cv2
import numpy as np
import OpenEXR

from .cases import CASES, RegressionCase, find_cases

BASE_DIR = Path(__file__).resolve().parents[1]
RVLIB_PATH = BASE_DIR.parents[1] / "rvlib" / "rvlib"
GOLDEN_DIR = BASE_DIR / "golden"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
SUPPORTED_IMAGE_SUFFIXES = {
    ".exr",
    ".png",
    ".jpg",
    ".jpeg",
    ".bmp",
    ".tif",
    ".tiff",
    ".webp",
}


class RegressionError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageComparison:
    relative_path: Path
    mean_abs_diff: float
    max_abs_diff: int


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run rv render regression tests.")
    parser.add_argument(
        "--case",
        action="append",
        dest="cases",
        default=[],
        help="Run only the named regression case. Can be specified multiple times.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="Print available regression case names and exit.",
    )
    parser.add_argument(
        "--regen",
        action="store_true",
        help="Regenerate golden outputs instead of comparing against them.",
    )
    parser.add_argument(
        "--keep-render",
        action="store_true",
        help="Keep temporary render directories for inspection.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.list:
        for case in CASES:
            print(case.name)
        return 0

    selected = set(args.cases)
    cases = find_cases(selected if selected else None)
    if selected:
        missing = sorted(selected - {case.name for case in cases})
        if missing:
            raise SystemExit(f"Unknown regression case(s): {', '.join(missing)}")

    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    for case in cases:
        try:
            run_case(case, regen=args.regen, keep_render=args.keep_render)
            mode = "regenerated" if args.regen else "passed"
            print(f"[{mode}] {case.name}")
        except RegressionError as exc:
            failures.append(f"{case.name}: {exc}")
            print(f"[failed] {case.name}: {exc}", file=sys.stderr)

    if failures:
        print("\nRegression failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    return 0


def run_case(case: RegressionCase, regen: bool, keep_render: bool) -> None:
    if not case.script.is_file():
        raise RegressionError(f"script not found: {case.script}")

    temp_root = Path(tempfile.mkdtemp(prefix=f"rv-regression-{case.name}-"))
    try:
        sample_dir = render_case(case, temp_root)
        if regen:
            regen_case(case, sample_dir)
            return
        compare_case(case, sample_dir)
    finally:
        if keep_render:
            print(f"[kept] {case.name}: {temp_root}")
        else:
            shutil.rmtree(temp_root, ignore_errors=True)


def render_case(case: RegressionCase, temp_root: Path) -> Path:
    render_root = temp_root / "render"
    go_cache = temp_root / "gocache"
    render_root.mkdir(parents=True, exist_ok=True)
    go_cache.mkdir(parents=True, exist_ok=True)

    cmd = [
        "go",
        "run",
        "../..",
        "render",
        str(case.script),
        "-n",
        str(case.image_number),
        "-p",
        str(case.procs),
        "-o",
        str(render_root),
        "--cwd",
        str(case.cwd),
        "--resolution",
        f"{case.resolution[0]},{case.resolution[1]}",
        "--seed",
        str(case.seed),
        "--gpu-backend",
        case.gpu_backend,
        "--max-samples",
        str(case.max_samples),
        "--time-limit",
        str(case.time_limit),
        *case.args,
    ]

    proc = subprocess.run(
        cmd,
        cwd=BASE_DIR,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "GOCACHE": str(go_cache),
            "RVLIB_PATH": str(RVLIB_PATH),
        },
    )
    if proc.returncode != 0:
        raise RegressionError(
            "render command failed\n"
            f"command: {' '.join(cmd)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )

    outputs = sorted(path for path in render_root.iterdir() if path.is_dir())
    if len(outputs) != 1:
        raise RegressionError(
            f"expected exactly one dataset output directory, found {len(outputs)}"
        )

    samples = sorted(path for path in outputs[0].iterdir() if path.is_dir())
    if len(samples) != case.image_number:
        raise RegressionError(
            f"expected {case.image_number} sample directories, found {len(samples)}"
        )

    return samples[0]


def regen_case(case: RegressionCase, sample_dir: Path) -> None:
    golden_case_dir = GOLDEN_DIR / case.name
    if golden_case_dir.exists():
        shutil.rmtree(golden_case_dir)
    shutil.copytree(sample_dir, golden_case_dir)


def compare_case(case: RegressionCase, sample_dir: Path) -> None:
    golden_case_dir = GOLDEN_DIR / case.name
    if not golden_case_dir.is_dir():
        raise RegressionError(
            f"missing golden output: {golden_case_dir} (run with --regen)"
        )

    expected = collect_image_files(golden_case_dir)
    actual = collect_image_files(sample_dir)

    expected_paths = set(expected)
    actual_paths = set(actual)
    missing = sorted(str(path) for path in expected_paths - actual_paths)
    unexpected = sorted(str(path) for path in actual_paths - expected_paths)
    problems: list[str] = []
    if missing:
        problems.append(f"missing image files: {', '.join(missing)}")
    if unexpected:
        problems.append(f"unexpected image files: {', '.join(unexpected)}")

    comparisons: list[ImageComparison] = []
    for relative_path in sorted(expected_paths & actual_paths):
        comparison = compare_images(
            relative_path,
            golden_case_dir / relative_path,
            sample_dir / relative_path,
            case,
        )
        comparisons.append(comparison)
        if (
            comparison.mean_abs_diff > case.mean_epsilon
            or comparison.max_abs_diff > case.max_epsilon
        ):
            diff_path = write_diff_artifact(
                case,
                relative_path,
                golden_case_dir / relative_path,
                sample_dir / relative_path,
            )
            problems.append(
                f"{relative_path}: mean diff {comparison.mean_abs_diff:.2f} "
                f"(limit {case.mean_epsilon:.2f}), max diff {comparison.max_abs_diff} "
                f"(limit {case.max_epsilon}); diff: {diff_path}"
            )

    if problems:
        raise RegressionError("; ".join(problems))

    if comparisons:
        worst = max(
            comparisons, key=lambda item: (item.mean_abs_diff, item.max_abs_diff)
        )
        print(
            f"  compared {len(comparisons)} image(s), "
            f"worst={worst.relative_path} mean={worst.mean_abs_diff:.2f} "
            f"max={worst.max_abs_diff}"
        )


def collect_image_files(root: Path) -> dict[Path, Path]:
    files: dict[Path, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SUPPORTED_IMAGE_SUFFIXES:
            continue
        files[path.relative_to(root)] = path
    return files


def compare_images(
    relative_path: Path,
    expected_path: Path,
    actual_path: Path,
    case: RegressionCase,
) -> ImageComparison:
    expected, actual = preprocess_image_pair(expected_path, actual_path, case)
    if expected.shape != actual.shape:
        raise RegressionError(
            f"shape mismatch for {expected_path.name}: {expected.shape} != {actual.shape}"
        )

    diff = cv2.absdiff(expected, actual)
    return ImageComparison(
        relative_path=relative_path,
        mean_abs_diff=float(np.mean(diff)),
        max_abs_diff=int(np.max(diff)),
    )


def preprocess_image_pair(
    expected_path: Path,
    actual_path: Path,
    case: RegressionCase,
) -> tuple[np.ndarray, np.ndarray]:
    expected = read_image(expected_path)
    actual = read_image(actual_path)

    expected, actual = align_channel_counts(expected, actual)
    expected = resize_image(expected, case.compare_size)
    actual = resize_image(actual, case.compare_size)
    expected, actual = normalize_image_pair(expected, actual)
    expected = lossy_roundtrip(expected, case)
    actual = lossy_roundtrip(actual, case)
    return expected, actual


def read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        if path.suffix.lower() == ".exr":
            return read_exr_image(path)
        raise RegressionError(f"failed to read image with OpenCV: {path}")
    return image


def read_exr_image(path: Path) -> np.ndarray:
    try:
        with OpenEXR.File(str(path)) as exr_file:
            part = exr_file.parts[0]
            channels = {
                name: np.asarray(channel.pixels)
                for name, channel in part.channels.items()
            }
    except Exception as exc:
        raise RegressionError(f"failed to read EXR image: {path}: {exc}") from exc

    preferred_orders = [
        ("B", "G", "R", "A"),
        ("B", "G", "R"),
        ("V",),
        ("Z",),
        ("Y",),
    ]
    for order in preferred_orders:
        if all(name in channels for name in order):
            arrays = [channels[name] for name in order]
            return np.stack(arrays, axis=2) if len(arrays) > 1 else arrays[0]

    ordered_names = sorted(channels.keys())
    if not ordered_names:
        raise RegressionError(f"EXR image has no channels: {path}")
    arrays = [channels[name] for name in ordered_names]
    return np.stack(arrays, axis=2) if len(arrays) > 1 else arrays[0]


def align_channel_counts(expected: np.ndarray, actual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    expected = ensure_channel_dim(expected)
    actual = ensure_channel_dim(actual)

    channels = max(expected.shape[2], actual.shape[2])
    return coerce_channels(expected, channels), coerce_channels(actual, channels)


def ensure_channel_dim(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2:
        return image[:, :, np.newaxis]
    return image


def coerce_channels(image: np.ndarray, channels: int) -> np.ndarray:
    current = image.shape[2]
    if current == channels:
        return image
    if current == 1 and channels == 3:
        return np.repeat(image, 3, axis=2)
    if current == 1 and channels == 4:
        repeated = np.repeat(image, 3, axis=2)
        alpha = np.full((*image.shape[:2], 1), fill_value=255, dtype=repeated.dtype)
        return np.concatenate([repeated, alpha], axis=2)
    if current == 3 and channels == 4:
        alpha = np.full((*image.shape[:2], 1), fill_value=255, dtype=image.dtype)
        return np.concatenate([image, alpha], axis=2)
    raise RegressionError(f"unsupported channel conversion: {current} -> {channels}")


def normalize_image_pair(expected: np.ndarray, actual: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if expected.dtype == np.uint8 and actual.dtype == np.uint8:
        return expected, actual

    if np.issubdtype(expected.dtype, np.integer) and np.issubdtype(actual.dtype, np.integer):
        max_value = float(max(np.iinfo(expected.dtype).max, np.iinfo(actual.dtype).max))
        return (
            np.clip(expected.astype(np.float32) * (255.0 / max_value), 0.0, 255.0).astype(np.uint8),
            np.clip(actual.astype(np.float32) * (255.0 / max_value), 0.0, 255.0).astype(np.uint8),
        )

    expected_f = expected.astype(np.float32)
    actual_f = actual.astype(np.float32)
    finite_values = np.concatenate(
        [
            expected_f[np.isfinite(expected_f)],
            actual_f[np.isfinite(actual_f)],
        ]
    )
    if finite_values.size == 0:
        return (
            np.zeros_like(expected_f, dtype=np.uint8),
            np.zeros_like(actual_f, dtype=np.uint8),
        )

    min_value = float(np.min(finite_values))
    max_value = float(np.max(finite_values))
    if min_value == max_value:
        return (
            np.zeros_like(expected_f, dtype=np.uint8),
            np.zeros_like(actual_f, dtype=np.uint8),
        )

    scale = 255.0 / (max_value - min_value)
    return (
        np.clip((expected_f - min_value) * scale, 0.0, 255.0).astype(np.uint8),
        np.clip((actual_f - min_value) * scale, 0.0, 255.0).astype(np.uint8),
    )


def lossy_roundtrip(image: np.ndarray, case: RegressionCase) -> np.ndarray:
    if image.ndim != 3:
        raise RegressionError(f"expected image with channels, got shape {image.shape}")

    if image.shape[2] == 4:
        color = image[:, :, :3]
        alpha = image[:, :, 3]
        color_decoded = lossy_roundtrip_jpeg(color, case.jpeg_quality, cv2.IMREAD_COLOR)
        alpha_decoded = lossy_roundtrip_jpeg(alpha, case.jpeg_quality, cv2.IMREAD_GRAYSCALE)
        return np.dstack([color_decoded, alpha_decoded])

    if image.shape[2] == 3:
        return lossy_roundtrip_jpeg(image, case.jpeg_quality, cv2.IMREAD_COLOR)

    if image.shape[2] == 1:
        decoded = lossy_roundtrip_jpeg(image[:, :, 0], case.jpeg_quality, cv2.IMREAD_GRAYSCALE)
        return decoded[:, :, np.newaxis]

    raise RegressionError(f"unsupported channel count: {image.shape[2]}")


def lossy_roundtrip_jpeg(image: np.ndarray, quality: int, imread_flag: int) -> np.ndarray:
    ok, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality],
    )
    if not ok:
        raise RegressionError("failed to JPEG-encode image")

    decoded = cv2.imdecode(encoded, imread_flag)
    if decoded is None:
        raise RegressionError("failed to JPEG-decode image")
    return decoded


def resize_image(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    if image.ndim == 3 and image.shape[2] == 1 and resized.ndim == 2:
        return resized[:, :, np.newaxis]
    return resized


def write_diff_artifact(
    case: RegressionCase,
    relative_path: Path,
    expected_path: Path,
    actual_path: Path,
) -> Path:
    artifact_dir = ARTIFACTS_DIR / case.name / relative_path.parent
    artifact_dir.mkdir(parents=True, exist_ok=True)

    expected, actual = preprocess_image_pair(expected_path, actual_path, case)
    diff = cv2.absdiff(expected, actual)

    stem = relative_path.stem
    expected_artifact = artifact_dir / f"{stem}.expected.png"
    actual_artifact = artifact_dir / f"{stem}.actual.png"
    diff_artifact = artifact_dir / f"{stem}.diff.png"

    cv2.imwrite(str(expected_artifact), expected)
    cv2.imwrite(str(actual_artifact), actual)
    cv2.imwrite(str(diff_artifact), diff)
    return diff_artifact


if __name__ == "__main__":
    raise SystemExit(main())
