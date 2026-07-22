#!/usr/bin/env bash
# Local smoke checks (mirrors CI).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Required skill files"
for skill in lora-dataset-prep fal-lora-training; do
  test -f "skills/${skill}/SKILL.md" || { echo "missing SKILL.md for ${skill}"; exit 1; }
done

echo "==> SKILL.md frontmatter"
python3 - <<'PY'
from pathlib import Path
import re
import sys

for skill in ("lora-dataset-prep", "fal-lora-training"):
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
print("frontmatter ok")
PY

echo "==> Python syntax"
python3 -m py_compile \
  skills/lora-dataset-prep/scripts/portrait_common.py \
  skills/lora-dataset-prep/scripts/prepare_all_portraits.py \
  skills/lora-dataset-prep/scripts/qc_flags.py \
  skills/lora-dataset-prep/scripts/manual_recrop.py \
  skills/lora-dataset-prep/scripts/recaption_dataset.py \
  skills/fal-lora-training/scripts/validate_dataset.py \
  skills/fal-lora-training/scripts/train_portrait_lora.py

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

echo "==> All checks passed"
