# Contributing

Thanks for helping improve these Cursor skills. Small, focused PRs are easiest to review.

## Ways to contribute

- Bug fixes in the Python helpers under `skills/*/scripts/`
- Clearer skill instructions in `SKILL.md` / `references/`
- Better crop / QC / caption heuristics (with rationale)
- Docs, install UX, and CI improvements
- Related portrait-LoRA skills that fit this repo’s scope

## Development setup

```bash
git clone https://github.com/shahshrey/fal-portrait-lora-skills.git
cd fal-portrait-lora-skills

# Optional: install skills into your Cursor personal skills dir for live testing
./scripts/install.sh

# Local venv + YuNet for script work
bash skills/lora-dataset-prep/scripts/setup_env.sh .
source .venv/bin/activate
```

Never commit `.env`, datasets, ZIPs, ONNX weights, or LoRA `.safetensors` files.

## Workflow

1. Open an issue first for larger changes (new behavior, API changes, new skills).
2. Fork the repo and create a branch from `main`:
   ```bash
   git checkout -b fix/short-description
   ```
3. Make focused changes. Prefer extending `portrait_common.py` over duplicating face-detection / QC policy.
4. Keep scripts importable as modules from their `scripts/` directory.
5. Run the smoke checks locally (same as CI):
   ```bash
   ./scripts/check.sh
   ```
6. Open a pull request using the PR template. Link related issues.

## Coding standards

- Prefer one canonical helper over parallel pipelines with drifting behavior.
- Keep skill docs and scripts in sync (paths, defaults, CLI flags).
- Captions for the portrait trainer must start with exact `[trigger]`.
- Do not add paid fal submission paths without an explicit confirmation gate (`--yes` / user confirmation).
- Avoid committing generated artifacts (`prepared_dataset/`, contact sheets, training JSON with secrets).

## Review expectations

Maintainers look for:

- Correctness and clear failure modes
- Structural simplicity (delete complexity when possible)
- Docs that a new contributor can follow without tribal knowledge
- No secrets or personal training data

## Reporting bugs

Use the Bug report issue template. Include:

- Skill name (`lora-dataset-prep` or `fal-lora-training`)
- Command(s) run
- Expected vs actual behavior
- OS / Python version
- Sanitized logs (redact keys and private paths)

## License

By contributing, you agree that your contributions are licensed under the MIT License.
