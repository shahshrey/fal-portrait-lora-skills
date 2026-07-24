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
names=()
for dir in "${ROOT}"/skills/*/; do
  skill="$(basename "$dir")"
  rm -rf "${DEST}/${skill}"
  cp -R "$dir" "${DEST}/${skill}"
  rm -rf "${DEST}/${skill}/scripts/__pycache__"
  names+=("/${skill}")
  echo "Installed ${skill} -> ${DEST}/${skill}"
done

echo "Done. Restart Agent chat or invoke ${names[*]}."
