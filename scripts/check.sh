#!/usr/bin/env bash
# Local smoke checks (mirrors CI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Checks must not leave __pycache__ behind.
export PYTHONDONTWRITEBYTECODE=1

echo "==> Required skill files"
shopt -s nullglob
skills=()
for dir in skills/*/; do
  skill="$(basename "$dir")"
  test -f "${dir}SKILL.md" || { echo "missing SKILL.md for ${skill}"; exit 1; }
  skills+=("$skill")
done
test "${#skills[@]}" -gt 0 || { echo "no skills found under skills/"; exit 1; }
echo "found: ${skills[*]}"

echo "==> SKILL.md frontmatter"
python3 - <<'PY'
from pathlib import Path
import re
import sys

skills = sorted(p.name for p in Path("skills").iterdir() if p.is_dir())
for skill in skills:
    text = Path(f"skills/{skill}/SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---"):
        sys.exit(f"{skill}: SKILL.md must start with YAML frontmatter")
    end = text.find("\n---", 3)
    if end < 0:
        sys.exit(f"{skill}: missing closing frontmatter")
    fm = text[3:end]
    if not re.search(r"^name:\s*.+", fm, re.M):
        sys.exit(f"{skill}: missing name")
    if not re.search(r"^description:\s*.+", fm, re.M | re.S):
        sys.exit(f"{skill}: missing description")
    name = re.search(r"^name:\s*(.+)$", fm, re.M).group(1).strip()
    if name != skill:
        sys.exit(f"{skill}: frontmatter name={name!r} must match folder")
print(f"frontmatter ok ({len(skills)} skills)")
PY

echo "==> Python syntax"
python3 - <<'PY'
import ast
import sys
from pathlib import Path

paths = sorted(Path("skills").glob("*/scripts/*.py"))
if not paths:
    sys.exit("no skill scripts found")
for path in paths:
    try:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        sys.exit(f"{path}: {exc}")
print(f"parsed {len(paths)} script(s)")
PY

echo "==> Caption contract unit check"
python3 - <<'PY'
import importlib.util
import sys
import tempfile
import zipfile
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "validate_dataset",
    Path("skills/fal-lora-training/scripts/validate_dataset.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    zpath = tmp / "ok.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for i in range(10):
            name = f"subject_{i:03d}"
            zf.writestr(f"{name}.jpg", b"fake")
            zf.writestr(f"{name}.txt", "[trigger], portrait photo\n")
    mod.validate_archive(zpath, require_placeholder=True, minimum_images=10)

    bad = tmp / "bad.zip"
    with zipfile.ZipFile(bad, "w") as zf:
        for i in range(10):
            name = f"subject_{i:03d}"
            zf.writestr(f"{name}.jpg", b"fake")
            zf.writestr(f"{name}.txt", "ohwx man, portrait photo\n")
    try:
        mod.validate_archive(bad, require_placeholder=True, minimum_images=10)
    except ValueError as exc:
        assert "must start with [trigger]" in str(exc)
    else:
        sys.exit("expected placeholder startswith validation to fail")
print("validate_dataset ok")
PY

echo "==> Inference prompt contract unit check"
python3 - <<'PY'
import argparse
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "generate_lora_images",
    Path("skills/fal-lora-inference/scripts/generate_lora_images.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

assert mod.parse_image_size("portrait_4_3") == "portrait_4_3"
assert mod.parse_image_size("1280x720") == {"width": 1280, "height": 720}
try:
    mod.parse_image_size("huge")
except argparse.ArgumentTypeError:
    pass
else:
    sys.exit("expected invalid image size to be rejected")


def args(prompts, trigger, require=True):
    return SimpleNamespace(
        prompt=prompts,
        prompts_file=None,
        trigger_phrase=trigger,
        require_trigger=require,
    )


# The trigger carries the identity, so a prompt without it must not be sent.
assert mod.collect_prompts(args(["ohwx man, portrait"], "ohwx man")) == [
    "ohwx man, portrait"
]
try:
    mod.collect_prompts(args(["a portrait of a man"], "ohwx man"))
except SystemExit as exc:
    assert "omit the trigger phrase" in str(exc)
else:
    sys.exit("expected missing trigger to be rejected")

# Opting out is allowed explicitly, for base-model comparison shots.
assert mod.collect_prompts(args(["a portrait"], None, require=False)) == ["a portrait"]

try:
    mod.collect_prompts(args([], "ohwx man"))
except SystemExit as exc:
    assert "at least one --prompt" in str(exc)
else:
    sys.exit("expected empty prompt list to be rejected")

jobs = mod.build_jobs(["ohwx man, portrait"], [0.8, 1.0])
assert [job["scale"] for job in jobs] == [0.8, 1.0]
assert jobs[0]["stem"] == "01_s0.8_ohwx_man_portrait"
print("generate_lora_images ok")
PY

echo "==> All checks passed"
