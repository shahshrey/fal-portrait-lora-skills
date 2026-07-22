#!/usr/bin/env python3
"""Generate descriptive LoRA captions with Florence-2 + trigger token."""

from __future__ import annotations

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from dotenv import load_dotenv

from portrait_common import SUPPORTED, zip_flat_dataset

MODEL = "fal-ai/florence-2-large/more-detailed-caption"

FLUFF = [
    r"\s*The overall mood of the image is[^.]*\.?",
    r"\s*He looks happy and relaxed\.?",
    r"\s*his eyes are bright and full of life\.?",
    r"\s*He seems to be engaged in a conversation with someone on the laptop\.?",
    r"\s*He appears to be in his late twenties or early thirties(?: and)?[^.]*\.?",
    r"\s*he appears to be in his late twenties or early thirties(?: and)?[^.]*\.?",
    r"\s*He appears to have a slight smile on his lips\.?",
    r"\s*highlighting his features\.?",
]


def ensure_fal_key(env_file: Path | None = None):
    if env_file and env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()
    if os.getenv("FAL_API_KEY") and not os.getenv("FAL_KEY"):
        os.environ["FAL_KEY"] = os.getenv("FAL_API_KEY")
    if not os.getenv("FAL_KEY"):
        raise SystemExit("Missing FAL_KEY or FAL_API_KEY for captioning")


def polish_caption(raw: str, trigger: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    text = re.sub(r"^The image is (a |an )?", "", text, flags=re.I)
    text = re.sub(r"^This (image )?shows ", "", text, flags=re.I)
    text = re.sub(r"^This (image )?is (a |an )?", "", text, flags=re.I)
    text = re.sub(r"^The image shows ", "", text, flags=re.I)
    text = re.sub(r"^A photo of ", "", text, flags=re.I)
    text = re.sub(
        r"^An? (close-?up |medium |tight |outdoor |indoor )?(portrait|selfie|photo) of ",
        "",
        text,
        flags=re.I,
    )

    for pat in FLUFF:
        text = re.sub(pat, " ", text, flags=re.I)

    text = re.sub(r"\bthe man's\b", "his", text, flags=re.I)
    text = re.sub(r"\ba man's\b", "his", text, flags=re.I)
    text = re.sub(
        r"\b(?:a|the)\s+(?:young\s+)?(?:handsome\s+|smiling\s+)?"
        r"(?:south\s+asian\s+|asian\s+)?man\b",
        "SUBJECT",
        text,
        flags=re.I,
    )
    text = re.sub(r"^SUBJECT\s+", "", text)
    text = re.sub(r"\bportrait of SUBJECT\b", "", text, flags=re.I)
    text = re.sub(r"\bselfie of SUBJECT\b", "", text, flags=re.I)
    text = re.sub(r"\bphoto of SUBJECT\b", "", text, flags=re.I)
    text = re.sub(r"\bclose-up of SUBJECT(?:'s)? face\b", "close-up", text, flags=re.I)
    text = re.sub(r"\bSUBJECT's face\b", "his face", text, flags=re.I)
    text = re.sub(r"\bSUBJECT's\b", "his", text, flags=re.I)
    text = re.sub(r"\bSUBJECT\b", "he", text)
    text = re.sub(r"\bportrait of he\b", "", text, flags=re.I)
    text = re.sub(r"\bselfie of he\b", "", text, flags=re.I)
    text = re.sub(r"\bclose-up of he(?:'s)? face\b", "close-up", text, flags=re.I)
    text = re.sub(r"\bhe's\b", "his", text, flags=re.I)

    shot = "portrait"
    if re.search(r"\bselfie\b", raw, re.I):
        shot = "selfie"
    elif re.search(r"\bclose-?up\b", raw, re.I):
        shot = "close-up portrait"

    text = re.sub(r"\s+", " ", text).strip(" ,.")
    if text.lower().startswith("wearing") or text.lower().startswith("with "):
        body = f"{shot}, {text[0].lower() + text[1:]}"
    else:
        body = text[0].lower() + text[1:] if text else shot

    caption = f"{trigger}, {body}"
    caption = re.sub(r"\s+", " ", caption).strip()
    caption = re.sub(r"\bclose-up\s+\.", "close-up portrait.", caption)
    caption = re.sub(
        r"\bclose-up\s+'s face", "close-up portrait", caption
    )
    caption = re.sub(
        r"\b(close-up )?portrait of his face",
        "close-up portrait",
        caption,
        flags=re.I,
    )
    caption = re.sub(r"\bof he\b", "of him", caption, flags=re.I)
    if not caption.endswith("."):
        caption += "."
    caption = caption.replace("..", ".")
    # Keep trigger casing exact; only capitalize later sentence starts carefully.
    parts = re.split(r"([.!?]\s+)", caption)
    out = []
    for i, part in enumerate(parts):
        if i == 0:
            out.append(part)  # preserve trigger case
        elif i % 2 == 0 and part:
            out.append(part[0].upper() + part[1:])
        else:
            out.append(part)
    return "".join(out)


def apply_caption_mode(
    caption: str, trigger: str, caption_mode: str
) -> str:
    if caption_mode == "literal":
        return caption
    return re.sub(
        rf"^{re.escape(trigger)}\b",
        "[trigger]",
        caption,
        count=1,
    )


def caption_one(path: Path, trigger: str, caption_mode: str) -> dict:
    import fal_client

    url = fal_client.upload_file(str(path))
    result = fal_client.subscribe(MODEL, arguments={"image_url": url})
    raw = result.get("results") or result.get("caption") or str(result)
    if isinstance(raw, dict):
        raw = raw.get("caption") or json.dumps(raw)
    polished = polish_caption(str(raw), trigger)
    polished = apply_caption_mode(polished, trigger, caption_mode)
    return {"file": path.name, "raw": str(raw), "caption": polished, "url": url}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--zip", type=Path, required=True)
    ap.add_argument("--trigger", default="ohwx man")
    ap.add_argument("--pattern", default="*.jpg", help="Glob under --images")
    ap.add_argument(
        "--caption-mode",
        choices=("placeholder", "literal"),
        default="placeholder",
        help="Use [trigger] for portrait trainer or the literal trigger text",
    )
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--env", type=Path, default=None, help="Optional .env path")
    args = ap.parse_args()

    ensure_fal_key(args.env)
    images = sorted(args.images.glob(args.pattern))
    images = [p for p in images if p.suffix.lower() in SUPPORTED]
    if not images:
        raise SystemExit(f"No images matched {args.images}/{args.pattern}")

    # Caption everything first; only touch dataset files once every image succeeded.
    print(f"Captioning {len(images)} images with {MODEL} ...")
    results = []
    failures = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {
            ex.submit(caption_one, p, args.trigger, args.caption_mode): p
            for p in images
        }
        for i, fut in enumerate(as_completed(futs), 1):
            p = futs[fut]
            try:
                item = fut.result()
                results.append(item)
                print(f"[{i}/{len(images)}] {p.name}: {item['caption'][:120]}")
            except Exception as e:
                failures.append(p.name)
                print(f"[{i}/{len(images)}] FAIL {p.name}: {e}")
    if failures:
        raise SystemExit(
            f"{len(failures)} captions failed ({', '.join(failures[:5])}...); "
            "no dataset files were modified."
        )

    results.sort(key=lambda x: x["file"])
    for item in results:
        txt = args.images / f"{Path(item['file']).stem}.txt"
        txt.write_text(item["caption"] + "\n", encoding="utf-8")
    report = args.images.parent / "captions.json"
    report.write_text(json.dumps(results, indent=2), encoding="utf-8")

    zip_flat_dataset(args.images, args.zip)

    print(f"\nWrote {report}")
    print(f"Updated zip {args.zip} ({args.zip.stat().st_size / 1e6:.1f} MB)")
    print("\nSamples:")
    for item in results[:5]:
        print(f"- {item['file']}: {item['caption']}")


if __name__ == "__main__":
    main()
