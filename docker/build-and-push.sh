#!/bin/bash
# Build and push Boltz inference Docker image
# Usage: ./build-and-push.sh [tag] [--slim]

set -e

# Configuration
REGISTRY="docker.io"
REPO="xingqiangchen/boltz-service"
TAG="${1:-latest}"
SLIM_MODE="${2:-}"

echo "========================================"
echo "Boltz Service Docker Build"
echo "========================================"
echo "Repository: ${REPO}"
echo "Tag: ${TAG}"
echo ""

cd "$(dirname "$0")/.."

if [ "$SLIM_MODE" == "--slim" ]; then
    echo "Building SLIM image (without embedded model)..."
    DOCKERFILE="docker/inference-slim.Dockerfile"
    FULL_TAG="${REPO}:${TAG}-slim"
else
    echo "Building FULL image (with embedded model ~7GB)..."
    echo "WARNING: This will download ~7GB of model weights during build."
    DOCKERFILE="docker/inference.Dockerfile"
    FULL_TAG="${REPO}:${TAG}"
fi

echo ""
echo "Dockerfile: ${DOCKERFILE}"
echo "Full tag: ${FULL_TAG}"
echo ""

# Build the image
echo "Step 1/3: Building Docker image..."
docker build \
    -f "${DOCKERFILE}" \
    -t "${FULL_TAG}" \
    --progress=plain \
    .

echo ""
echo "Step 2/3: Testing image..."
docker run --rm "${FULL_TAG}" python3 -c "
import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
from boltz_service.model.model import BoltzModel
print('BoltzModel import: OK')
"

echo ""
echo "Step 3/3: Pushing to Docker Hub..."
docker push "${FULL_TAG}"

echo ""
echo "========================================"
echo "BUILD COMPLETE!"
echo "========================================"
echo "Image: ${FULL_TAG}"
echo ""
echo "To run the service:"
if [ "$SLIM_MODE" == "--slim" ]; then
    echo "  docker run -d --gpus all \\"
    echo "    -p 50051:50051 \\"
    echo "    -v /path/to/models:/data/models \\"
    echo "    ${FULL_TAG}"
else
    echo "  docker run -d --gpus all \\"
    echo "    -p 50051:50051 \\"
    echo "    ${FULL_TAG}"
fi
echo ""
