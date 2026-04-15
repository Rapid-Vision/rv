import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def read_request() -> dict:
    raw = sys.stdin.read()
    if raw.strip() == "":
        raise ValueError("generator request is empty")
    return json.loads(raw)


def make_output_path(work_dir: str, seed: int | None) -> str:
    os.makedirs(work_dir, exist_ok=True)
    suffix = "none" if seed is None else str(seed)
    return os.path.join(work_dir, f"seed_{suffix}.png")


def draw_centered_text(
    draw: ImageDraw.ImageDraw, image_size: tuple[int, int], text: str, font
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (image_size[0] - text_width) / 2
    y = (image_size[1] - text_height) / 2
    draw.text((x, y), text, fill=(22, 27, 33), font=font)


def main() -> None:
    request = read_request()
    seed = request.get("seed")
    _root_dir = request["root_dir"]
    work_dir = request["work_dir"]
    output_path = make_output_path(work_dir, seed)

    width, height = 1024, 1024
    image = Image.new("RGB", (width, height), (242, 240, 233))
    draw = ImageDraw.Draw(image)

    margin = 40
    draw.rounded_rectangle(
        (margin, margin, width - margin, height - margin),
        radius=48,
        outline=(40, 40, 40),
        width=10,
        fill=(252, 251, 247),
    )

    text = str(seed)
    text = text[:10] + "\n" + text[10:]
    font = ImageFont.load_default(size=100)
    draw_centered_text(draw, (width, height), text, font)

    image.save(output_path)
    json.dump({"path": output_path}, sys.stdout)


if __name__ == "__main__":
    main()
