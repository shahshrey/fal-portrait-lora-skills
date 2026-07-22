---
name: fal-lora-training
license: MIT
description: >-
  Validates, uploads, submits, monitors, and persists fal portrait LoRA
  training runs using fal-ai/flux-lora-portrait-trainer. Use when the user asks
  to train, fine-tune, start, submit, or monitor a portrait/person LoRA from a
  prepared ZIP; or mentions images_data_url, trigger_phrase, portrait trainer,
  training steps, learning rate, LoRA weights, or a fal training request.
---

# fal Portrait LoRA Training

Train a prepared dataset with `fal-ai/flux-lora-portrait-trainer`.

## Defaults

| Setting | Default |
|---|---|
| Endpoint | `fal-ai/flux-lora-portrait-trainer` |
| Steps | `2500` |
| Learning rate | `0.00009` |
| Multiresolution | `true` |
| Subject crop | `true` |
| Create masks | `false` |
| Captions | Matching `.txt`, beginning with `[trigger]` |

## Paid-submission rule

Training is a paid external action.

- If the current user request explicitly says to start, submit, run, or train,
  proceed without asking twice.
- Otherwise, show endpoint and settings and ask for confirmation.
- Pass `--yes` only after one of those conditions is met.

## Workflow

Resolve the project-local skill first:

```bash
SKILL_DIR=".cursor/skills/fal-lora-training"
[ -d "$SKILL_DIR" ] || SKILL_DIR="$HOME/.cursor/skills/fal-lora-training"
[ -d "$SKILL_DIR" ] || SKILL_DIR="skills/fal-lora-training"
```

### 1. Validate the archive

```bash
.venv/bin/python "$SKILL_DIR/scripts/validate_dataset.py" \
  "/path/to/dataset.zip" \
  --require-placeholder
```

Do not submit unless validation passes. The archive must be flat, contain at
least ten images, pair every image with a same-stem `.txt`, and use `[trigger]`
captions.

### 2. Confirm settings

Ask if missing:

- Dataset ZIP path
- Trigger phrase
- Output directory for request/result JSON

Use defaults unless the user specifies different portrait-training values.
An endpoint override is allowed only when it accepts the same input schema.
See [references/portrait-trainer-schema.md](references/portrait-trainer-schema.md).

### 3. Submit and monitor

Run as a background command because training is long-running:

```bash
.venv/bin/python "$SKILL_DIR/scripts/train_portrait_lora.py" \
  --archive "/path/to/dataset.zip" \
  --trigger-phrase "ohwx man" \
  --output-dir "./portrait_training_run" \
  --env ".env" \
  --yes
```

The script:

1. Revalidates the ZIP.
2. Uploads it with `fal_client.upload_file`.
3. Submits `images_data_url` to the portrait endpoint.
4. Writes `training_request.json` immediately.
5. Waits for completion.
6. Writes `training_result.json` containing LoRA and config URLs.

After backgrounding, read the command output once to confirm it reached
`SUBMITTED request_id=...`. Rely on completion notification rather than
frequent polling.

### 4. Deliver

Report:

- Request ID
- Endpoint and settings
- Dataset image count
- Trigger phrase
- LoRA weights URL
- Config URL

## Authentication

Requires `fal-client` and either `FAL_KEY` or `FAL_API_KEY`. The script maps
`FAL_API_KEY` to the client-compatible `FAL_KEY` variable without printing it.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/validate_dataset.py` | Validate flat image/caption ZIP contract |
| `scripts/train_portrait_lora.py` | Upload, submit, monitor, persist results |
