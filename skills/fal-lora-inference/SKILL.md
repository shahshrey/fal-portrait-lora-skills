---
name: fal-lora-inference
license: MIT
description: >-
  Generates and evaluates images from a trained portrait LoRA using
  fal-ai/flux-lora, including LoRA scale sweeps, local image downloads, and
  review contact sheets. Use when the user asks to run inference, generate,
  render, sample, or test images from a LoRA; to check likeness or whether a
  LoRA is overtrained; or mentions flux-lora, lora_scale, safetensors weights,
  a trigger phrase in a prompt, guidance scale, image_size, or seeds.
---

# fal LoRA Inference

Generate images from trained LoRA weights with `fal-ai/flux-lora`, save them
locally, and judge whether the LoRA is usable.

## Defaults

| Setting | Default |
|---|---|
| Endpoint | `fal-ai/flux-lora` |
| LoRA scale | `1.0` |
| Image size | `portrait_4_3` |
| Inference steps | `28` |
| Guidance scale | `3.5` |
| Images per prompt | `1` |
| Output format | `jpeg` |
| Trigger in prompt | Required |

## Paid-submission rule

Generation is a paid external action.

- If the current user request explicitly says to generate, render, run
  inference, sample, or test the LoRA, proceed without asking twice.
- Otherwise, show the endpoint, prompts, and settings and ask for confirmation.
- Pass `--yes` only after one of those conditions is met.

Cost scales with prompts × scales × `--num-images`. State the total image count
before a large sweep.

## The trigger phrase is not optional

The trigger phrase carries the identity. A prompt without it renders a generic
person even though the LoRA loaded successfully, which reads as a broken LoRA.
The script refuses such prompts unless `--no-require-trigger` is passed.

## Workflow

Resolve the project-local skill first:

```bash
SKILL_DIR=".cursor/skills/fal-lora-inference"
[ -d "$SKILL_DIR" ] || SKILL_DIR="$HOME/.cursor/skills/fal-lora-inference"
[ -d "$SKILL_DIR" ] || SKILL_DIR="skills/fal-lora-inference"
```

### 1. Confirm inputs

Ask if missing:

- LoRA weights: a fal URL, or a local `.safetensors` path to upload
- Trigger phrase used at training time
- Prompts, or the intent to sweep with defaults
- Output directory

The trigger phrase and weights URL are recorded in `training_result.json` and
`training_request.json` if `fal-lora-training` produced this LoRA. Read them
instead of asking.

### 2. Sweep the LoRA scale

For an untested LoRA, start with one prompt across several scales at a fixed
seed so composition stays constant and scale is the only variable:

```bash
.venv/bin/python "$SKILL_DIR/scripts/generate_lora_images.py" \
  --lora "./portrait_training_run/subject_lora.safetensors" \
  --trigger-phrase "ohwx man" \
  --prompt "ohwx man, close-up portrait, soft window light, navy blazer" \
  --lora-scale 0.7 0.9 1.1 1.3 \
  --seed 12345 \
  --output-dir "./lora_generations/scale_sweep" \
  --env ".env" \
  --yes
```

### 3. Vary the prompts

Once a working scale is known, hold it and test range — shot distance,
lighting, wardrobe, setting, expression:

```bash
.venv/bin/python "$SKILL_DIR/scripts/generate_lora_images.py" \
  --lora "https://…/pytorch_lora_weights.safetensors" \
  --trigger-phrase "ohwx man" \
  --prompts-file "./prompts.txt" \
  --lora-scale 1.0 \
  --image-size portrait_16_9 \
  --num-images 2 \
  --output-dir "./lora_generations/prompt_set" \
  --env ".env" \
  --yes
```

`--prompts-file` takes one prompt per line and ignores blanks and `#` comments.

The script uploads a local LoRA if needed, runs prompts × scales concurrently,
downloads every image, writes `generations.json`, and renders
`contact_sheet.jpg`.

### 4. Review the output visually (required)

Open `contact_sheet.jpg` with image vision, then open individual files at full
resolution. Do not report success from exit codes alone — a completed request
says nothing about likeness.

Judge likeness, skin texture, eye consistency, prompt adherence, and pose
variety against
[references/evaluation-checklist.md](references/evaluation-checklist.md).

### 5. Deliver

Report:

- Working LoRA scale, and what failed outside it
- Whether the LoRA looks under- or overtrained, with the evidence
- Output directory and contact sheet path
- Seeds worth reusing
- Any failed requests

Recommend a retrain only with a specific reason, such as likeness needing
`1.3`, or training wardrobe persisting across every prompt.

## Authentication

Requires `fal-client`, `python-dotenv`, and either `FAL_KEY` or `FAL_API_KEY`.
The script maps `FAL_API_KEY` to the client-compatible `FAL_KEY` without
printing it. `pillow` is optional and only powers the contact sheet.

## Scripts

| Script | Purpose |
|---|---|
| `scripts/generate_lora_images.py` | Upload LoRA, run prompt × scale matrix, download images, write manifest and contact sheet |

## Degrees of freedom

- **Low**: trigger phrase present in every prompt, local downloads, visual
  review before reporting
- **Medium**: prompt wording, image size, steps, guidance, seeds
- **High**: which scales to sweep, and whether results justify a retrain

See [references/flux-lora-schema.md](references/flux-lora-schema.md) for the
full input and output schema.
