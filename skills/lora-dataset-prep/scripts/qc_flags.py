#!/usr/bin/env python3
"""Flag suspicious portrait crops after prepare (advisory, not auto-reject)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from portrait_common import (
    SUPPORTED,
    average_hash,
    detect_primary_face,
    flag_reasons,
    hamming,
    load_rgb,
)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--pattern", default="*.jpg")
    ap.add_argument("--report", type=Path, default=None, help="Optional JSON output path")
    ap.add_argument(
        "--dedupe-threshold",
        type=int,
        default=12,
        help="Max perceptual-hash distance to flag near-duplicates",
    )
    ap.add_argument("--delete-flagged", action="store_true", help="Delete flagged jpg+txt pairs")
    args = ap.parse_args()

    images = sorted(args.images.glob(args.pattern))
    images = [p for p in images if p.suffix.lower() in SUPPORTED]
    if not images:
        raise SystemExit(f"No images matched {args.images}/{args.pattern}")

    flagged = []
    seen_hashes: list[tuple[str, str]] = []
    for p in images:
        image = load_rgb(p)
        face = detect_primary_face(image, args.model, score_threshold=0.5)
        reasons = flag_reasons(face)

        phash = average_hash(image)
        duplicate_of = next(
            (
                name
                for name, prev in seen_hashes
                if hamming(phash, prev) <= args.dedupe_threshold
            ),
            None,
        )
        if duplicate_of:
            reasons.append(f"near_duplicate_of:{duplicate_of}")
        seen_hashes.append((p.name, phash))

        if reasons:
            flagged.append({"file": p.name, "reasons": reasons, "meta": face})
            print(f"[flag] {p.name}: {', '.join(reasons)}")
            if args.delete_flagged:
                p.unlink(missing_ok=True)
                p.with_suffix(".txt").unlink(missing_ok=True)
                print(f"  deleted {p.name}")

    report = {
        "scanned": len(images),
        "flagged_count": len(flagged),
        "flagged": flagged,
    }
    report_path = args.report or (args.images.parent / "qc_flags.json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n=== QC FLAGS ===")
    print(f"scanned: {len(images)}")
    print(f"flagged: {len(flagged)}")
    print(f"report:  {report_path}")
    if flagged and not args.delete_flagged:
        print("Review flagged files, delete bad ones, then re-zip / recaption.")


if __name__ == "__main__":
    main()
