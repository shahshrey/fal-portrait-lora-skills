#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-}"

if [[ "$MODE" == "--project" ]]; then
  DEST="$(pwd)/.cursor/skills"
elif [[ "$MODE" == "" || "$MODE" == "--user" ]]; then
  DEST="${HOME}/.cursor/skills"
else
  echo "Usage: $0 [--user|--project]" >&2
  exit 1
fi

mkdir -p "$DEST"
for skill in lora-dataset-prep fal-lora-training; do
  rm -rf "${DEST}/${skill}"
  cp -R "${ROOT}/skills/${skill}" "${DEST}/${skill}"
  echo "Installed ${skill} -> ${DEST}/${skill}"
done

echo "Done. Restart Agent chat or invoke /lora-dataset-prep and /fal-lora-training."
