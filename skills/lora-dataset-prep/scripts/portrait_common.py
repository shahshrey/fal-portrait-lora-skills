#!/usr/bin/env python3
"""Shared face-detection, QC-policy, and artifact helpers for dataset prep."""

from __future__ import annotations

import zipfile
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

TARGET = 1024
SUPPORTED = {".jpg", ".jpeg", ".png", ".webp"}
DATASET_SUFFIXES = {".jpg", ".jpeg", ".png", ".txt"}


def load_rgb(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGB")


def detect_primary_face(
    image: Image.Image, model_path: Path, score_threshold: float = 0.45
) -> dict | None:
    """Detect the most likely subject face and return normalized metadata."""
    bgr = cv2.cvtColor(np.asarray(image), cv2.COLOR_RGB2BGR)
    h, w = bgr.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(model_path), "", (w, h), score_threshold, 0.3, 5000
    )
    detector.setInputSize((w, h))
    _, faces = detector.detect(bgr)
    if faces is None or len(faces) == 0:
        return None

    cx0, cy0 = w / 2, h / 2

    # YuNet rows are [x, y, w, h, 10 landmark coords, score]; the score is last.
    def unpack(face):
        x, y, fw, fh = map(float, face[:4])
        return x, y, fw, fh, float(face[-1])

    def rank(face):
        x, y, fw, fh, confidence = unpack(face)
        cx, cy = x + fw / 2, y + fh / 2
        distance = np.hypot((cx - cx0) / w, (cy - cy0) / h)
        area = (fw * fh) / (w * h)
        return confidence * np.sqrt(area) / (0.12 + distance)

    x, y, fw, fh, confidence = unpack(max(faces, key=rank))
    return {
        "x": x,
        "y": y,
        "w": fw,
        "h": fh,
        "confidence": confidence,
        "face_count": len(faces),
        "area_frac": (fw * fh) / float(w * h),
        "cx": (x + fw / 2) / w,
        "cy": (y + fh / 2) / h,
        "top_margin": y / h,
    }


def flag_reasons(face: dict | None) -> list[str]:
    """Advisory framing flags for an already-cropped portrait."""
    if face is None:
        return ["no_face"]
    reasons = []
    if face["area_frac"] < 0.055:
        reasons.append(f"face_too_small:{face['area_frac']:.3f}")
    if face["area_frac"] > 0.50:
        reasons.append(f"face_too_tight:{face['area_frac']:.3f}")
    if not (0.30 <= face["cx"] <= 0.70):
        reasons.append(f"face_offcenter_x:{face['cx']:.2f}")
    if not (0.28 <= face["cy"] <= 0.62):
        reasons.append(f"face_offcenter_y:{face['cy']:.2f}")
    if face["top_margin"] < 0.015 and face["cy"] < 0.35:
        reasons.append("hair_clipped")
    if face["confidence"] < 0.55:
        reasons.append(f"low_face_score:{face['confidence']:.2f}")
    if face["face_count"] >= 2:
        reasons.append(f"multi_face:{face['face_count']}")
    return reasons


def average_hash(image: Image.Image, hash_size: int = 16) -> str:
    small = image.convert("L").resize(
        (hash_size, hash_size), Image.Resampling.BILINEAR
    )
    pixels = list(small.getdata())
    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if p >= avg else "0" for p in pixels)
    return f"{int(bits, 2):0{hash_size * hash_size // 4}x}"


def hamming(a: str, b: str) -> int:
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def make_contact_sheets(
    images: list[Path], output_dir: Path, per_sheet: int = 36
):
    sheet_dir = output_dir / "contact_sheets"
    sheet_dir.mkdir(parents=True, exist_ok=True)
    for old in sheet_dir.glob("*.jpg"):
        old.unlink()

    cols, thumb, label_h = 6, 220, 32
    font = ImageFont.load_default()
    for start in range(0, len(images), per_sheet):
        batch = images[start : start + per_sheet]
        rows = (len(batch) + cols - 1) // cols
        sheet = Image.new(
            "RGB", (cols * thumb, rows * (thumb + label_h)), (20, 20, 20)
        )
        draw = ImageDraw.Draw(sheet)
        for offset, path in enumerate(batch):
            image = Image.open(path).convert("RGB").resize(
                (thumb, thumb), Image.Resampling.LANCZOS
            )
            x = (offset % cols) * thumb
            y = (offset // cols) * (thumb + label_h)
            sheet.paste(image, (x, y))
            draw.rectangle(
                (x, y + thumb, x + thumb, y + thumb + label_h),
                fill=(8, 8, 8),
            )
            draw.text(
                (x + 4, y + thumb + 4),
                f"{start + offset + 1:03d} {path.name}",
                fill="white",
                font=font,
            )
        sheet.save(
            sheet_dir / f"contact_{start // per_sheet + 1:02d}.jpg",
            quality=92,
        )


def zip_flat_dataset(images_dir: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(images_dir.iterdir()):
            if p.suffix.lower() in DATASET_SUFFIXES:
                zf.write(p, arcname=p.name)
