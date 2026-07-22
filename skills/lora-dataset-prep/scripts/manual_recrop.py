#!/usr/bin/env python3
"""Apply a visually chosen crop and refresh dataset review artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageOps

from portrait_common import TARGET, make_contact_sheets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path, required=True)
    parser.add_argument("--output-name", required=True)
    parser.add_argument(
        "--box",
        type=int,
        nargs=4,
        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
        required=True,
    )
    args = parser.parse_args()

    if Path(args.output_name).name != args.output_name:
        raise SystemExit("--output-name must be a filename, not a path")
    if Path(args.output_name).suffix.lower() != ".jpg":
        raise SystemExit("--output-name must end in .jpg")

    image = ImageOps.exif_transpose(Image.open(args.source)).convert("RGB")
    left, top, right, bottom = args.box
    if not (0 <= left < right <= image.width):
        raise SystemExit(f"Invalid horizontal crop for width {image.width}")
    if not (0 <= top < bottom <= image.height):
        raise SystemExit(f"Invalid vertical crop for height {image.height}")
    if right - left != bottom - top:
        raise SystemExit("Manual crop box must be square")

    images_dir = args.dataset_root / "images"
    output = images_dir / args.output_name
    if not output.exists():
        raise SystemExit(f"Prepared output does not exist: {output}")

    cropped = image.crop(tuple(args.box)).resize(
        (TARGET, TARGET), Image.Resampling.LANCZOS
    )
    cropped.save(
        output, "JPEG", quality=95, optimize=True, subsampling=0
    )

    manifest_path = args.dataset_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [item for item in manifest if item["output"] == args.output_name]
    if len(matches) != 1:
        raise SystemExit(
            f"Expected one manifest item for {args.output_name}; "
            f"found {len(matches)}"
        )
    item = matches[0]
    item["source"] = args.source.name
    item["crop_box"] = list(args.box)
    item["method"] = "manual_visual_qa"
    manifest_path.write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )

    outputs = sorted(images_dir.glob("*.jpg"))
    make_contact_sheets(outputs, args.dataset_root)
    print(f"Corrected {output}")
    print(f"Updated {manifest_path}")
    print(f"Regenerated {args.dataset_root / 'contact_sheets'}")


if __name__ == "__main__":
    main()
