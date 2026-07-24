# fal Portrait LoRA Skills

Open-source [Cursor Agent Skills](https://cursor.com/docs) covering the whole portrait LoRA loop: prepare a dataset, train it with [`fal-ai/flux-lora-portrait-trainer`](https://fal.ai), then generate and evaluate images with [`fal-ai/flux-lora`](https://fal.ai/models/fal-ai/flux-lora/api).

| Skill | What it does |
|---|---|
| [`lora-dataset-prep`](skills/lora-dataset-prep/) | Face-centered 1024×1024 crops, contact-sheet visual QA, Florence-2 captions, flat ZIP packing |
| [`fal-lora-training`](skills/fal-lora-training/) | Validate ZIP → upload → submit → monitor → persist LoRA weights |
| [`fal-lora-inference`](skills/fal-lora-inference/) | Generate from trained weights, sweep LoRA scale, download images, contact sheet for review |

These skills teach an agent the workflow end-to-end, and ship the Python helpers the agent runs.

## Install

### Cursor (recommended)

1. Clone or download this repo.
2. Copy (or symlink) the skill folders into your Cursor skills directory:

```bash
# Personal (all projects)
mkdir -p ~/.cursor/skills
cp -R skills/* ~/.cursor/skills/

# Or project-local
mkdir -p .cursor/skills
cp -R skills/* .cursor/skills/
```

3. In Agent chat, invoke with `/lora-dataset-prep`, `/fal-lora-training`, or `/fal-lora-inference` — or just ask to prepare, train, or test a portrait LoRA, and the agent should pick them up from the skill descriptions.

### One-liner helper

```bash
./scripts/install.sh            # installs into ~/.cursor/skills
./scripts/install.sh --project  # installs into ./.cursor/skills
```

## Quick start

```bash
# 1) Dataset prep env + YuNet model
bash ~/.cursor/skills/lora-dataset-prep/scripts/setup_env.sh

# 2) Crop every source photo for review
.venv/bin/python ~/.cursor/skills/lora-dataset-prep/scripts/prepare_all_portraits.py \
  --src "/path/to/raw_photos" \
  --out "./prepared_dataset" \
  --model "./models/face_detection_yunet_2023mar.onnx" \
  --prefix "subject"

# 3) Visually QA contact sheets, manually recrop failures, then caption + zip
# (see skills/lora-dataset-prep/SKILL.md)

# 4) Train (paid fal job — requires explicit confirmation / --yes)
.venv/bin/python ~/.cursor/skills/fal-lora-training/scripts/train_portrait_lora.py \
  --archive "./prepared_dataset/dataset.zip" \
  --trigger-phrase "ohwx man" \
  --output-dir "./portrait_training_run" \
  --env ".env" \
  --yes

# 5) Test the LoRA across scales (paid fal job) and review the contact sheet
.venv/bin/python ~/.cursor/skills/fal-lora-inference/scripts/generate_lora_images.py \
  --lora "./portrait_training_run/subject_lora.safetensors" \
  --trigger-phrase "ohwx man" \
  --prompt "ohwx man, close-up portrait, soft window light, navy blazer" \
  --lora-scale 0.7 0.9 1.1 1.3 \
  --seed 12345 \
  --output-dir "./lora_generations" \
  --env ".env" \
  --yes
```

The trigger phrase must appear in every prompt — it is what carries the identity. A prompt without it renders a generic person even with the LoRA loaded.

Auth for captioning, training, and inference: set `FAL_KEY` or `FAL_API_KEY` in a local `.env` (never commit it).

## Repository layout

```text
skills/
  lora-dataset-prep/     # dataset prep skill + scripts
  fal-lora-training/     # fal training skill + scripts
  fal-lora-inference/    # generation + evaluation skill + scripts
scripts/
  install.sh             # copy skills into Cursor
  check.sh               # smoke checks (same script CI runs)
.github/                 # issue/PR templates, CI, CODEOWNERS
```

## Requirements

- Python 3.10+
- Cursor (for skill invocation) or any agent that loads Agent Skills (`SKILL.md`)
- Optional: fal account + API key for captioning and training

## Contributing

Contributions are welcome — bug fixes, better crop heuristics, caption polish, docs, and new related skills.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow, coding standards, and review expectations.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) before participating.

## Security

Do not open issues with API keys, private photos, or training URLs you consider sensitive.
Report security issues privately per [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE) © 2026 Shrey Shah

fal.ai, FLUX, and Cursor are trademarks of their respective owners. This project is not affiliated with or endorsed by fal, Black Forest Labs, or Anysphere.
