#!/usr/bin/env bash
set -euo pipefail
CACHE_DIR="${BOLTZ_CACHE_DIR:-/data/cache}"
MODEL_DIR="${CACHE_DIR}/models/v1"
MODEL_URL="${BOLTZ_MODEL_URL:-https://hf-mirror.com/boltz-community/boltz-1/resolve/main/boltz1.ckpt}"
mkdir -p "${MODEL_DIR}" /opt/model
if [[ ! -f "${MODEL_DIR}/model.ckpt" ]]; then
  if [[ -f /opt/model/boltz1.ckpt ]]; then
    cp /opt/model/boltz1.ckpt "${MODEL_DIR}/model.ckpt"
  else
    echo "Downloading model to ${MODEL_DIR}/model.ckpt"
    wget -q --show-progress -O "${MODEL_DIR}/model.ckpt" "${MODEL_URL}"
  fi
fi
echo "Model ready at ${MODEL_DIR}/model.ckpt"
