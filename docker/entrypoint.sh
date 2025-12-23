#!/bin/bash
set -e

# Check if model files exist, download if not
MODEL_PATH="${BOLTZ_MODEL_PATH:-/data/models/boltz1.ckpt}"
CCD_PATH="${BOLTZ_CCD_PATH:-/data/models/ccd.pkl}"
HF_MIRROR="${HF_ENDPOINT:-https://hf-mirror.com}"

echo "Boltz Inference Service Starting..."
echo "Model path: $MODEL_PATH"
echo "CCD path: $CCD_PATH"

# Download model if not present
if [ ! -f "$MODEL_PATH" ]; then
    echo "Model not found. Downloading from $HF_MIRROR..."
    mkdir -p "$(dirname $MODEL_PATH)"
    wget -q --show-progress -O "$MODEL_PATH" \
        "${HF_MIRROR}/boltz-community/boltz-1/resolve/main/boltz1.ckpt"
    echo "Model downloaded successfully."
fi

# Download CCD if not present
if [ ! -f "$CCD_PATH" ]; then
    echo "CCD data not found. Downloading from $HF_MIRROR..."
    mkdir -p "$(dirname $CCD_PATH)"
    wget -q --show-progress -O "$CCD_PATH" \
        "${HF_MIRROR}/boltz-community/boltz-1/resolve/main/ccd.pkl"
    echo "CCD data downloaded successfully."
fi

# Verify files
if [ -f "$MODEL_PATH" ] && [ -f "$CCD_PATH" ]; then
    MODEL_SIZE=$(du -h "$MODEL_PATH" | cut -f1)
    CCD_SIZE=$(du -h "$CCD_PATH" | cut -f1)
    echo "Model: $MODEL_SIZE, CCD: $CCD_SIZE"
    echo "All dependencies ready!"
else
    echo "ERROR: Required files missing!"
    exit 1
fi

# Execute the main command
exec "$@"
