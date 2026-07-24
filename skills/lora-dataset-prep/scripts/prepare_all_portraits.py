#!/usr/bin/env python3
"""Crop every source into a reviewable 1024px portrait dataset."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from portrait_common import (
    SUPPORTED,
    TARGET,
    detect_primary_face,
    load_rgb,
    make_contact_sheets,
)


def crop_box(image: Image.Image, face: dict | None):
    w, h = image.size
    side = min(w, h)
    if face is None:
        left = (w - side) // 2
        top = (h - side) // 2
        return (left, top, left + side, top + side), "center_fallback"

    face_side = max(face["w"], face["h"])
    # Floor the crop at native TARGET so distant faces stay as tight as possible
    # without upscaling past 1:1.
    wanted = max(face_side * 4.2, min(min(w, h), TARGET))
    side = int(min(wanted, min(w, h)))
    cx = face["x"] + face["w"] / 2
    cy = face["y"] + face["h"] * 0.50
    left = int(np.clip(round(cx - side / 2), 0, w - side))
    top = int(np.clip(round(cy - side * 0.42), 0, h - side))
    return (left, top, left + side, top + side), "face_centered"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--prefix", default="subject")
    parser.add_argument("--per-sheet", type=int, default=36)
    args = parser.parse_args()

    if args.out.exists():
        shutil.rmtree(args.out)
    images_dir = args.out / "images"
    images_dir.mkdir(parents=True)

    sources = sorted(
        [p for p in args.src.iterdir() if p.suffix.lower() in SUPPORTED],
        key=lambda p: p.name.lower(),
    )
    if not sources:
        raise SystemExit(f"No supported images found in {args.src}")

    manifest = []
    outputs = []
    for index, source in enumerate(sources, 1):
        image = load_rgb(source)
        face = detect_primary_face(image, args.model)
        box, method = crop_box(image, face)
        cropped = image.crop(box).resize(
            (TARGET, TARGET), Image.Resampling.LANCZOS
        )
        output = images_dir / f"{args.prefix}_{index:03d}.jpg"
        cropped.save(
            output, "JPEG", quality=95, optimize=True, subsampling=0
        )
        output.with_suffix(".txt").write_text(
            "[trigger], portrait photo\n", encoding="utf-8"
        )
        outputs.append(output)
        manifest.append(
            {
                "index": index,
                "source": source.name,
                "output": output.name,
                "source_size": list(image.size),
                "crop_box": list(box),
                "method": method,
                "face": face,
            }
        )
        print(f"[{index:03d}/{len(sources)}] {source.name} -> {method}")

    (args.out / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    make_contact_sheets(outputs, args.out, args.per_sheet)
    print(f"Prepared {len(outputs)} images in {images_dir}")
    print(f"Review every sheet in {args.out / 'contact_sheets'}")


if __name__ == "__main__":
    main()
