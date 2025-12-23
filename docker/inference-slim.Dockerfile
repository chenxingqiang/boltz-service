# Boltz Inference Service Dockerfile (Slim Version)
# Model weights are mounted at runtime via volume
# Suitable for environments with pre-downloaded models

FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

LABEL maintainer="xingqiangchen"
LABEL description="Boltz Protein Structure Prediction Service (Slim)"
LABEL version="1.0.0"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src
ENV PATH="/opt/venv/bin:$PATH"

# Model and cache paths (to be mounted)
ENV BOLTZ_CACHE_DIR=/data/cache
ENV BOLTZ_MODEL_PATH=/data/models/boltz1.ckpt
ENV BOLTZ_CCD_PATH=/data/models/ccd.pkl
ENV HF_ENDPOINT=https://hf-mirror.com

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

WORKDIR /app

# Create virtual environment
RUN python3 -m venv /opt/venv

# Copy dependency files first for caching
COPY pyproject.toml setup.py requirements.txt ./

# Install PyTorch for CUDA 12.1
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

# Copy source code and install package
COPY README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir -e .

# Create directories
RUN mkdir -p /data/cache /data/models /data/output

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)" || exit 1

# Expose gRPC port
EXPOSE 50051

# Entrypoint script to download models if not present
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python3", "-m", "boltz_service.main", "--mode", "inference"]
