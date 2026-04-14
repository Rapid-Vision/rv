import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


def read_request() -> dict:
    raw = sys.stdin.read()
    if raw.strip() == "":
        raise ValueError("generator request is empty")
    return json.loads(raw)


def make_output_path(cwd: str, seed: int | None) -> str:
    output_dir = os.path.join(cwd, "generated")
    os.makedirs(output_dir, exist_ok=True)
    suffix = "none" if seed is None else str(seed)
    return os.path.join(output_dir, f"seed_{suffix}.png")


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
    cwd = request["cwd"]
    output_path = make_output_path(cwd, seed)

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
    print(seed, len(text), file=sys.stderr)
    font = ImageFont.load_default(size=100)
    draw_centered_text(draw, (width, height), text, font)

    image.save(output_path)
    json.dump({"path": output_path}, sys.stdout)


if __name__ == "__main__":
    main()
