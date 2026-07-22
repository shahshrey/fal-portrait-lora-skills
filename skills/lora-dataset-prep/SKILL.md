---
name: lora-dataset-prep
license: MIT
description: >-
  Prepares portrait LoRA training datasets: face-centered 1024x1024 crops,
  mandatory visual QA and manual crop correction, contact sheets, ZIP packing,
  and descriptive [trigger] captions via Florence-2. Use when preparing images
  for FLUX portrait training, fal-ai/flux-lora-portrait-trainer, Kohya, or
  person LoRA training; or when the user mentions dataset prep, captioning
  training images, cropping faces for LoRA, or building training ZIP archives.
---

# LoRA Dataset Prep

Prepare a fal/FLUX-compatible portrait LoRA dataset from a raw photo folder.

## Defaults

| Setting | Default |
|---|---|
| Size | 1024×1024 JPEG |
| Trigger phrase | `ohwx man` (ask user; keep unique) |
| Caption identity token | `[trigger]` |
| Filename prefix | `subject` |
| Image policy | Keep user-curated images unless visual QA finds a real defect |
| ZIP layout | flat: `name.jpg` + matching `name.txt` |

## Workflow

Copy and track:

```
Progress:
- [ ] 1. Setup env + YuNet model
- [ ] 2. Confirm trigger word + source/out paths
- [ ] 3. Crop every source + generate numbered contact sheets
- [ ] 4. Visually inspect every crop; manually correct failures
- [ ] 5. Descriptive captions with trigger
- [ ] 6. Validate pairs + build flat ZIP; report counts
```

Resolve skill path (project copy preferred):

```bash
SKILL_DIR=".cursor/skills/lora-dataset-prep"
[ -d "$SKILL_DIR" ] || SKILL_DIR="$HOME/.cursor/skills/lora-dataset-prep"
[ -d "$SKILL_DIR" ] || SKILL_DIR="skills/lora-dataset-prep"
```

### 1. Setup

From the project working directory:

```bash
bash "$SKILL_DIR/scripts/setup_env.sh"
```

Deps: Python 3, `opencv-python-headless`, `pillow`, `numpy`, `fal-client`, `python-dotenv`.  
Auth for captioning: `FAL_KEY` or `FAL_API_KEY` in `.env`.

### 2. Confirm inputs

Ask if missing:
- Source image folder
- Output folder (default: `./prepared_dataset`)
- Trigger token (default: `ohwx man`)
- Subject filename prefix (default: `subject`)

### 3. Crop every source

```bash
.venv/bin/python "$SKILL_DIR/scripts/prepare_all_portraits.py" \
  --src "/path/to/raw_photos" \
  --out "./prepared_dataset" \
  --model "./models/face_detection_yunet_2023mar.onnx" \
  --prefix "subject"
```

Produces:
- `prepared_dataset/images/*.jpg` + `[trigger]` placeholder `.txt`
- `prepared_dataset/contact_sheets/*.jpg`
- `prepared_dataset/manifest.json`

The detector proposes crops; it does not decide whether an image is usable.
Do not discard an image solely because detection fails or its face is distant.

### 4. Visual QA and correction (required)

First generate advisory flags:

```bash
.venv/bin/python "$SKILL_DIR/scripts/qc_flags.py" \
  --images "./prepared_dataset/images" \
  --model "./models/face_detection_yunet_2023mar.onnx" \
  --pattern "subject_*.jpg"
```

Writes `prepared_dataset/qc_flags.json`, including `near_duplicate_of` flags
for burst shots. Treat these flags as review prompts, not automatic rejection
decisions.

Then use image vision to open **every** file under
`prepared_dataset/contact_sheets/`, not only the automated flags:

1. Confirm the intended subject appears correctly in every numbered crop.
2. Open suspicious outputs and their source files at full resolution.
3. Manually recrop wrong-subject, torso-only, clipped, or off-center outputs.
4. Regenerate contact sheets and inspect the corrected cells.
5. Record manual crop boxes in `manifest.json`.

Apply each visually chosen square crop reproducibly:

```bash
.venv/bin/python "$SKILL_DIR/scripts/manual_recrop.py" \
  --source "/path/to/raw_photos/source.jpg" \
  --dataset-root "./prepared_dataset" \
  --output-name "subject_068.jpg" \
  --box 882 320 2422 1860
```

The helper replaces the crop, records `manual_visual_qa` in the manifest, and
regenerates all contact sheets. Reopen the affected sheet and verify it.

Never use `--delete-flagged` without visually confirming each deletion.
See [references/qc-checklist.md](references/qc-checklist.md).

### 5. Caption

Prefer descriptive per-image captions over a single shared caption.

```bash
.venv/bin/python "$SKILL_DIR/scripts/recaption_dataset.py" \
  --images "./prepared_dataset/images" \
  --zip "./prepared_dataset/dataset.zip" \
  --trigger "ohwx man" \
  --pattern "subject_*.jpg" \
  --caption-mode placeholder \
  --workers 8
```

Caption rules: [references/caption-rules.md](references/caption-rules.md).

### 6. Deliver

Report:
- Kept / rejected counts
- Trigger word
- ZIP path
- 3–5 sample captions

Ready for `fal-ai/flux-lora-portrait-trainer` as `images_data_url` with
`trigger_phrase` set to the chosen trigger.

## Scripts

| Script | Role |
|---|---|
| `scripts/setup_env.sh` | venv, pip deps, download YuNet ONNX |
| `scripts/portrait_common.py` | shared face detection, QC policy, hashing, sheets, ZIP |
| `scripts/prepare_all_portraits.py` | crop all images + split contact sheets |
| `scripts/manual_recrop.py` | apply visual crop + update manifest/sheets |
| `scripts/qc_flags.py` | framing + near-duplicate flags → `qc_flags.json` |
| `scripts/recaption_dataset.py` | Florence-2 captions + polish + re-zip |

## Degrees of freedom

- **Low**: 1024 crops, visual review of every contact sheet, flat ZIP pairs,
  `[trigger]` first in captions
- **Medium**: crop framing and automated flag thresholds
- **High**: manual crop corrections and whether a visibly defective source
  should be excluded
