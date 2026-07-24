#!/usr/bin/env python3
"""Generate images from a trained LoRA with fal-ai/flux-lora and save them locally."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

DEFAULT_ENDPOINT = "fal-ai/flux-lora"
NAMED_SIZES = (
    "square_hd",
    "square",
    "portrait_4_3",
    "portrait_16_9",
    "landscape_4_3",
    "landscape_16_9",
)
# A portrait LoRA is judged on faces, so default away from the endpoint's
# landscape_4_3 and toward a vertical frame.
DEFAULT_SIZE = "portrait_4_3"


def parse_image_size(value: str):
    if value in NAMED_SIZES:
        return value
    match = re.fullmatch(r"(\d{2,4})x(\d{2,4})", value.strip().lower())
    if not match:
        raise argparse.ArgumentTypeError(
            f"--image-size must be WIDTHxHEIGHT or one of: {', '.join(NAMED_SIZES)}"
        )
    return {"width": int(match.group(1)), "height": int(match.group(2))}


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lora",
        required=True,
        help="LoRA weights: a fal URL, or a local .safetensors path to upload",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        default=[],
        metavar="TEXT",
        help="Prompt to render; repeat the flag for several prompts",
    )
    parser.add_argument(
        "--prompts-file",
        type=Path,
        help="Text file with one prompt per line (blank lines and # ignored)",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--trigger-phrase",
        help="Identity token; every prompt must contain it unless --no-require-trigger",
    )
    parser.add_argument(
        "--require-trigger",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refuse prompts that omit the trigger phrase",
    )
    parser.add_argument(
        "--lora-scale",
        type=float,
        nargs="+",
        default=[1.0],
        metavar="SCALE",
        help="LoRA strength; pass several values to sweep every prompt across them",
    )
    parser.add_argument("--image-size", type=parse_image_size, default=DEFAULT_SIZE)
    parser.add_argument("--num-images", type=int, default=1)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance-scale", type=float, default=3.5)
    parser.add_argument(
        "--seed",
        type=int,
        help="Fix the seed so prompts and scales stay visually comparable",
    )
    parser.add_argument("--output-format", choices=("jpeg", "png"), default="jpeg")
    parser.add_argument(
        "--acceleration", choices=("none", "regular"), default="none"
    )
    parser.add_argument(
        "--endpoint",
        default=DEFAULT_ENDPOINT,
        help="Override only for an endpoint with the same input schema",
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--env", type=Path, default=None)
    parser.add_argument(
        "--contact-sheet",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Write a labeled grid of every generation for review",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm authorization for the paid generation request",
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


def collect_prompts(args) -> list[str]:
    prompts = list(args.prompt)
    if args.prompts_file:
        for line in args.prompts_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                prompts.append(line)
    if not prompts:
        raise SystemExit("Provide at least one --prompt or a --prompts-file")

    trigger = (args.trigger_phrase or "").strip()
    if args.require_trigger:
        if not trigger:
            raise SystemExit(
                "--trigger-phrase is required; pass --no-require-trigger to "
                "generate without the LoRA identity token"
            )
        missing = [p for p in prompts if trigger.lower() not in p.lower()]
        if missing:
            listed = "\n".join(f"  - {p}" for p in missing)
            raise SystemExit(
                f"These prompts omit the trigger phrase {trigger!r}, so the LoRA "
                f"identity will not be applied:\n{listed}"
            )
    return prompts


def resolve_lora(reference: str) -> str:
    if reference.startswith(("http://", "https://")):
        return reference
    path = Path(reference).expanduser()
    if not path.is_file():
        raise SystemExit(f"LoRA not found: {path}")

    import fal_client

    print(f"Uploading {path} ({path.stat().st_size / 1e6:.1f} MB)", flush=True)
    return fal_client.upload_file(str(path))


def slugify(text: str, limit: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:limit].rstrip("_") or "prompt"


def build_jobs(prompts: list[str], scales: list[float]) -> list[dict]:
    jobs = []
    for prompt_index, prompt in enumerate(prompts, 1):
        for scale in scales:
            jobs.append(
                {
                    "prompt": prompt,
                    "scale": scale,
                    "stem": f"{prompt_index:02d}_s{scale:g}_{slugify(prompt)}",
                }
            )
    return jobs


def run_job(job: dict, lora_url: str, args) -> dict:
    import fal_client

    arguments = {
        "prompt": job["prompt"],
        "loras": [{"path": lora_url, "scale": job["scale"]}],
        "image_size": args.image_size,
        "num_inference_steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "num_images": args.num_images,
        "output_format": args.output_format,
        "acceleration": args.acceleration,
    }
    if args.seed is not None:
        arguments["seed"] = args.seed
    result = fal_client.subscribe(args.endpoint, arguments=arguments)
    return {**job, "arguments": arguments, "result": result}


def download_images(record: dict, images_dir: Path, output_format: str) -> list[str]:
    saved = []
    images = record["result"].get("images") or []
    for index, image in enumerate(images, 1):
        url = image.get("url")
        if not url:
            continue
        suffix = "png" if output_format == "png" else "jpg"
        name = record["stem"]
        if len(images) > 1:
            name = f"{name}_{index}"
        target = images_dir / f"{name}.{suffix}"
        urllib.request.urlretrieve(url, target)
        saved.append(target.name)
    return saved


def write_contact_sheet(records: list[dict], images_dir: Path, target: Path) -> bool:
    """Grid every generation with its scale and prompt so results are reviewable."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("Pillow not installed; skipping contact sheet", flush=True)
        return False

    files = [
        (record, images_dir / name)
        for record in records
        for name in record.get("saved", [])
    ]
    files = [(record, path) for record, path in files if path.is_file()]
    if not files:
        return False

    cell, label = 320, 34
    columns = min(4, len(files))
    rows = (len(files) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell, rows * (cell + label)), "white")
    draw = ImageDraw.Draw(sheet)

    for index, (record, path) in enumerate(files):
        with Image.open(path) as img:
            thumb = img.convert("RGB")
            thumb.thumbnail((cell, cell))
            x = (index % columns) * cell + (cell - thumb.width) // 2
            y = (index // columns) * (cell + label)
            sheet.paste(thumb, (x, y + (cell - thumb.height) // 2))
        caption = f"scale {record['scale']:g} | {record['prompt'][:52]}"
        draw.text(
            ((index % columns) * cell + 6, (index // columns) * (cell + label) + cell + 8),
            caption,
            fill="black",
        )

    sheet.save(target, quality=92)
    return True


def main():
    args = parse_args()
    if not args.yes:
        raise SystemExit(
            "Paid generation not authorized. Review settings and rerun with --yes."
        )
    if not 1 <= args.steps <= 100:
        raise SystemExit("--steps must be between 1 and 100")
    if not 1 <= args.num_images <= 8:
        raise SystemExit("--num-images must be between 1 and 8")
    for scale in args.lora_scale:
        if not 0.0 <= scale <= 2.0:
            raise SystemExit("--lora-scale values must be between 0.0 and 2.0")

    prompts = collect_prompts(args)
    load_credentials(args.env)

    images_dir = args.output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    lora_url = resolve_lora(args.lora)
    jobs = build_jobs(prompts, args.lora_scale)
    total = len(jobs) * args.num_images
    print(
        f"Generating {total} image(s): {len(prompts)} prompt(s) x "
        f"{len(args.lora_scale)} scale(s) x {args.num_images} per request",
        flush=True,
    )

    records, failures = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_job, job, lora_url, args): job for job in jobs}
        for done, future in enumerate(as_completed(futures), 1):
            job = futures[future]
            try:
                record = future.result()
            except Exception as exc:
                failures.append(
                    {
                        "prompt": job["prompt"],
                        "scale": job["scale"],
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                    }
                )
                print(f"[{done}/{len(jobs)}] FAILED {job['stem']}: {exc}", flush=True)
                continue
            record["saved"] = download_images(record, images_dir, args.output_format)
            records.append(record)
            print(
                f"[{done}/{len(jobs)}] {job['stem']} -> "
                f"{', '.join(record['saved']) or 'no image returned'}",
                flush=True,
            )

    records.sort(key=lambda r: r["stem"])
    manifest = {
        "endpoint": args.endpoint,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "lora_url": lora_url,
        "lora_source": args.lora,
        "trigger_phrase": args.trigger_phrase,
        "lora_scales": args.lora_scale,
        "image_size": args.image_size,
        "num_inference_steps": args.steps,
        "guidance_scale": args.guidance_scale,
        "seed": args.seed,
        "generations": [
            {
                "prompt": record["prompt"],
                "scale": record["scale"],
                "files": record["saved"],
                "seed": record["result"].get("seed"),
                "has_nsfw_concepts": record["result"].get("has_nsfw_concepts"),
                "image_urls": [
                    img.get("url") for img in record["result"].get("images") or []
                ],
            }
            for record in records
        ],
        "failures": failures,
    }
    manifest_path = args.output_dir / "generations.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    if args.contact_sheet:
        sheet = args.output_dir / "contact_sheet.jpg"
        if write_contact_sheet(records, images_dir, sheet):
            print(f"Contact sheet {sheet}", flush=True)

    saved_count = sum(len(record["saved"]) for record in records)
    print(f"\nSaved {saved_count} image(s) to {images_dir}", flush=True)
    print(f"Manifest {manifest_path}", flush=True)
    if failures:
        raise SystemExit(f"{len(failures)} of {len(jobs)} request(s) failed")


if __name__ == "__main__":
    main()
