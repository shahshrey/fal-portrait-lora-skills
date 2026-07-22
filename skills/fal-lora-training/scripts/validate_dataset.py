#!/usr/bin/env python3
"""Validate a flat image/caption ZIP for fal portrait LoRA training."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def validate_archive(
    archive: Path,
    *,
    require_placeholder: bool = False,
    minimum_images: int = 10,
) -> dict:
    if not archive.is_file():
        raise ValueError(f"Archive does not exist: {archive}")
    if not zipfile.is_zipfile(archive):
        raise ValueError(f"Not a valid ZIP archive: {archive}")

    with zipfile.ZipFile(archive) as zf:
        names = [name for name in zf.namelist() if not name.endswith("/")]
        nested = [name for name in names if "/" in name or "\\" in name]
        if nested:
            raise ValueError(
                f"Archive must be flat; nested entries found: {nested[:5]}"
            )

        image_names = [
            name
            for name in names
            if Path(name).suffix.lower() in IMAGE_EXTENSIONS
        ]
        caption_names = [
            name for name in names if Path(name).suffix.lower() == ".txt"
        ]
        if len(image_names) < minimum_images:
            raise ValueError(
                f"Need at least {minimum_images} images; found {len(image_names)}"
            )

        image_stems = [Path(name).stem for name in image_names]
        caption_stems = [Path(name).stem for name in caption_names]
        if len(image_stems) != len(set(image_stems)):
            raise ValueError("Duplicate image stems found")
        if len(caption_stems) != len(set(caption_stems)):
            raise ValueError("Duplicate caption stems found")

        missing_captions = sorted(set(image_stems) - set(caption_stems))
        orphan_captions = sorted(set(caption_stems) - set(image_stems))
        if missing_captions:
            raise ValueError(
                f"Images missing captions: {missing_captions[:10]}"
            )
        if orphan_captions:
            raise ValueError(
                f"Captions missing images: {orphan_captions[:10]}"
            )

        empty = []
        missing_placeholder = []
        for name in caption_names:
            caption = zf.read(name).decode("utf-8").strip()
            if not caption:
                empty.append(name)
            if require_placeholder and not caption.startswith("[trigger]"):
                missing_placeholder.append(name)
        if empty:
            raise ValueError(f"Empty captions: {empty[:10]}")
        if missing_placeholder:
            raise ValueError(
                "Captions must start with [trigger]: "
                f"{missing_placeholder[:10]}"
            )

    return {
        "archive": str(archive),
        "images": len(image_names),
        "captions": len(caption_names),
        "flat": True,
        "paired": True,
        "placeholder_required": require_placeholder,
        "placeholder_valid": not missing_placeholder,
        "size_bytes": archive.stat().st_size,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--require-placeholder", action="store_true")
    parser.add_argument("--minimum-images", type=int, default=10)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        result = validate_archive(
            args.archive,
            require_placeholder=args.require_placeholder,
            minimum_images=args.minimum_images,
        )
    except (ValueError, UnicodeDecodeError, zipfile.BadZipFile) as exc:
        raise SystemExit(f"INVALID: {exc}") from exc

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(
            f"VALID: {result['images']} images, "
            f"{result['captions']} captions, flat and paired"
        )


if __name__ == "__main__":
    main()
