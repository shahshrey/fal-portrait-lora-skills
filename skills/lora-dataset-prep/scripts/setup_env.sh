#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q --upgrade pip
pip install -q opencv-python-headless pillow numpy fal-client python-dotenv

mkdir -p models
MODEL="models/face_detection_yunet_2023mar.onnx"
if [[ ! -f "$MODEL" ]]; then
  curl -fsSL -o "$MODEL" \
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
fi

echo "Ready:"
echo "  venv:   $ROOT/.venv"
echo "  model:  $ROOT/$MODEL"
echo "  next:   activate .venv and run prepare_all_portraits.py"
