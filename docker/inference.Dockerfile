# Boltz Inference Service Dockerfile
# Optimized for production deployment with pre-downloaded model weights
# Uses Chinese HuggingFace mirror for faster downloads in China

# Stage 1: Base image with CUDA support
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04 AS base

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    wget \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

# Stage 2: Build stage for Python dependencies
FROM base AS builder

WORKDIR /build

# Copy dependency files first for caching
COPY pyproject.toml setup.py requirements.txt ./
COPY src/ ./src/

# Create virtual environment and install dependencies
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install PyTorch first (for CUDA 12.1)
RUN pip install --no-cache-dir \
    torch==2.1.0 \
    torchvision==0.16.0 \
    --index-url https://download.pytorch.org/whl/cu121

# Install gRPC dependencies
RUN pip install --no-cache-dir \
    grpcio>=1.54.2 \
    grpcio-tools>=1.54.2 \
    grpcio-health-checking>=1.54.2 \
    grpcio-reflection>=1.54.2 \
    protobuf>=4.23.2

# Install the package
RUN pip install --no-cache-dir -e .

# Stage 3: Download model weights
FROM base AS model-downloader

WORKDIR /models

# Use Chinese HuggingFace mirror for faster downloads
ENV HF_ENDPOINT=https://hf-mirror.com

# Download model checkpoint and CCD data
RUN wget -q --show-progress -O boltz1.ckpt \
    "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/boltz1.ckpt" \
    && wget -q --show-progress -O ccd.pkl \
    "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/ccd.pkl"

# Stage 4: Final production image
FROM base AS production

LABEL maintainer="xingqiangchen"
LABEL description="Boltz Protein Structure Prediction Service"
LABEL version="1.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV PATH="/opt/venv/bin:$PATH"

# Model and cache paths
ENV BOLTZ_CACHE_DIR=/data/cache
ENV BOLTZ_MODEL_PATH=/data/models/boltz1.ckpt
ENV BOLTZ_CCD_PATH=/data/models/ccd.pkl

# Service configuration
ENV GRPC_PORT=50051
ENV NUM_WORKERS=2
ENV DEVICES=1
ENV ACCELERATOR=gpu

# Default prediction parameters
ENV RECYCLING_STEPS=3
ENV SAMPLING_STEPS=200
ENV DIFFUSION_SAMPLES=1
ENV OUTPUT_FORMAT=mmcif

# Create app user for security
RUN groupadd -r boltz && useradd -r -g boltz boltz

# Create directories
RUN mkdir -p /app /data/cache /data/models /data/output \
    && chown -R boltz:boltz /app /data

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=boltz:boltz . .

# Copy model weights from downloader
COPY --from=model-downloader /models/boltz1.ckpt /data/models/
COPY --from=model-downloader /models/ccd.pkl /data/models/

# Ensure correct permissions
RUN chown -R boltz:boltz /data

# Switch to non-root user
USER boltz

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3 -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)" || exit 1

# Expose gRPC port
EXPOSE 50051

# Start the inference service
CMD ["python3", "-m", "boltz_service.main", "--mode", "inference"]
