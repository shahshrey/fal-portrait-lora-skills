#!/usr/bin/env python3
"""Validate, upload, submit, and monitor fal portrait LoRA training."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from validate_dataset import validate_archive

DEFAULT_ENDPOINT = "fal-ai/flux-lora-portrait-trainer"


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--trigger-phrase", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--env", type=Path, default=None)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--steps", type=int, default=2500)
    parser.add_argument("--learning-rate", type=float, default=0.00009)
    parser.add_argument(
        "--multiresolution-training",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--subject-crop",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument(
        "--create-masks",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm authorization for the paid training request",
    )
    return parser.parse_args()


def load_credentials(env_file: Path | None):
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()
    if os.getenv("FAL_API_KEY") and not os.getenv("FAL_KEY"):
        os.environ["FAL_KEY"] = os.environ["FAL_API_KEY"]
    if not os.getenv("FAL_KEY"):
        raise SystemExit("Missing FAL_KEY or FAL_API_KEY")


def write_json(path: Path, value: dict):
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def main():
    args = parse_args()
    if not args.yes:
        raise SystemExit(
            "Paid submission not authorized. Review settings and rerun with --yes."
        )
    if not 1 <= args.steps <= 10000:
        raise SystemExit("--steps must be between 1 and 10000")
    if not 0.000001 <= args.learning_rate <= 0.001:
        raise SystemExit(
            "--learning-rate must be between 0.000001 and 0.001"
        )
    if not args.trigger_phrase.strip():
        raise SystemExit("--trigger-phrase cannot be empty")

    validation = validate_archive(
        args.archive, require_placeholder=True, minimum_images=10
    )
    load_credentials(args.env)

    import fal_client

    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(
        f"VALIDATED images={validation['images']} "
        f"captions={validation['captions']}",
        flush=True,
    )
    print(
        f"Uploading {args.archive} "
        f"({args.archive.stat().st_size / 1e6:.1f} MB)",
        flush=True,
    )
    archive_url = fal_client.upload_file(str(args.archive))
    arguments = {
        "images_data_url": archive_url,
        "trigger_phrase": args.trigger_phrase,
        "learning_rate": args.learning_rate,
        "steps": args.steps,
        "multiresolution_training": args.multiresolution_training,
        "subject_crop": args.subject_crop,
        "create_masks": args.create_masks,
    }
    print(
        f"Upload complete; submitting {args.endpoint}",
        flush=True,
    )
    handler = fal_client.submit(args.endpoint, arguments=arguments)
    request = {
        "model_id": args.endpoint,
        "request_id": handler.request_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "dataset_images": validation["images"],
        **arguments,
    }
    write_json(args.output_dir / "training_request.json", request)
    print(f"SUBMITTED request_id={handler.request_id}", flush=True)

    try:
        result = handler.get()
    except Exception as exc:
        write_json(
            args.output_dir / "training_error.json",
            {
                "request_id": handler.request_id,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    write_json(args.output_dir / "training_result.json", result)
    print("TRAINING_COMPLETE", flush=True)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
