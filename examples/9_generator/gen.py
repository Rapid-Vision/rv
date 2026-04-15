import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont


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
    request = json.loads(sys.stdin.read())
    seed = request.get("seed")
    _root_dir = request["root_dir"]
    work_dir = request["work_dir"]
    output_path = os.path.join(work_dir, "texture.png")

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
    json.dump({"result": output_path}, sys.stdout)


if __name__ == "__main__":
    main()
