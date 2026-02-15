import argparse
from pathlib import Path

import cv2
import numpy as np


def _normalize_to_u8(image: np.ndarray) -> np.ndarray:
    image_f = image.astype(np.float32)
    min_v = float(image_f.min())
    max_v = float(image_f.max())

    if max_v == min_v:
        return np.zeros_like(image, dtype=np.uint8)

    normalized = (image_f - min_v) / (max_v - min_v)
    return (normalized * 255.0).clip(0, 255).astype(np.uint8)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Normalize an image to 0..255 and save or preview it."
    )
    parser.add_argument("image", type=Path, help="Path to the input image.")
    parser.add_argument(
        "-o",
        "--output",
        nargs="?",
        const="tmp.png",
        help="Save to output path. If provided without value, uses tmp.png.",
    )
    return parser


def preview() -> None:
    args = _build_parser().parse_args()

    image = cv2.imread(str(args.image), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise FileNotFoundError(f"Could not read image: {args.image}")

    normalized = _normalize_to_u8(image)

    if args.output is not None:
        output_path = Path(args.output)
        if not cv2.imwrite(str(output_path), normalized):
            raise RuntimeError(f"Failed to write image: {output_path}")
        return

    cv2.imshow("preview", normalized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
