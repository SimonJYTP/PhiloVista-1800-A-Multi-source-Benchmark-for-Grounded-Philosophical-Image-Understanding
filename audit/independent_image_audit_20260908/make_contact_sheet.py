from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


IMAGES = Path(r"D:\Project\哲学AI多模态论文\PhiloVista-1800-images")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--cols", type=int, default=4)
    args = parser.parse_args()

    cell_w, image_h, label_h = 480, 360, 42
    rows = (len(args.files) + args.cols - 1) // args.cols
    sheet = Image.new("RGB", (cell_w * args.cols, (image_h + label_h) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)

    for index, name in enumerate(args.files):
        path = IMAGES / name
        with Image.open(path) as im:
            tile = ImageOps.contain(im.convert("RGB"), (cell_w - 12, image_h - 12))
        col, row = index % args.cols, index // args.cols
        x = col * cell_w + (cell_w - tile.width) // 2
        y = row * (image_h + label_h) + (image_h - tile.height) // 2
        sheet.paste(tile, (x, y))
        draw.rectangle((col * cell_w, row * (image_h + label_h), (col + 1) * cell_w - 1, (row + 1) * (image_h + label_h) - 1), outline="#999999")
        draw.text((col * cell_w + 8, row * (image_h + label_h) + image_h + 8), name, fill="black", font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, quality=92)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
