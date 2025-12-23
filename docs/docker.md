# Docker Deployment Guide

This guide covers building and running Boltz Service using Docker.

## Image Variants

### Full Image (with model weights)

The full image includes pre-downloaded model weights (~7GB total size).

```bash
docker pull xingqiangchen/boltz-service:latest
```

### Slim Image (without model weights)

The slim image is lighter and downloads models on first run.

```bash
docker pull xingqiangchen/boltz-service:latest-slim
```

## Quick Start

### Running with GPU

```bash
# Full image (model embedded)
docker run -d --gpus all \
  -p 50051:50051 \
  --name boltz-service \
  xingqiangchen/boltz-service:latest

# Slim image (with external model volume)
docker run -d --gpus all \
  -p 50051:50051 \
  -v /path/to/models:/data/models \
  --name boltz-service \
  xingqiangchen/boltz-service:latest-slim
```

### Running without GPU (CPU only)

```bash
docker run -d \
  -p 50051:50051 \
  -e ACCELERATOR=cpu \
  --name boltz-service \
  xingqiangchen/boltz-service:latest
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BOLTZ_CACHE_DIR` | `/data/cache` | Directory for cache files |
| `BOLTZ_MODEL_PATH` | `/data/models/boltz1.ckpt` | Path to model checkpoint |
| `BOLTZ_CCD_PATH` | `/data/models/ccd.pkl` | Path to CCD data |
| `GRPC_PORT` | `50051` | gRPC service port |
| `NUM_WORKERS` | `2` | Number of data loader workers |
| `DEVICES` | `1` | Number of GPU devices |
| `ACCELERATOR` | `gpu` | Accelerator type (gpu/cpu) |
| `RECYCLING_STEPS` | `3` | Default recycling steps |
| `SAMPLING_STEPS` | `200` | Default sampling steps |
| `DIFFUSION_SAMPLES` | `1` | Default diffusion samples |
| `OUTPUT_FORMAT` | `mmcif` | Output format (mmcif/pdb) |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace mirror URL |

## Volumes

| Mount Point | Description |
|-------------|-------------|
| `/data/models` | Model weights directory (slim image) |
| `/data/cache` | Runtime cache for predictions |
| `/data/output` | Prediction output files |

## Building from Source

### Prerequisites

- Docker 20.10+
- NVIDIA Docker runtime (for GPU support)
- ~15GB disk space for full image

### Build Full Image

```bash
cd /path/to/boltz-service
docker build -f docker/inference.Dockerfile -t xingqiangchen/boltz-service:latest .
```

### Build Slim Image

```bash
cd /path/to/boltz-service
docker build -f docker/inference-slim.Dockerfile -t xingqiangchen/boltz-service:latest-slim .
```

### Using Build Script

```bash
# Build and push full image
./docker/build-and-push.sh latest

# Build and push slim image
./docker/build-and-push.sh latest --slim
```

## Model Download (Slim Image)

For the slim image, models are downloaded automatically on first run.
For China regions, the image uses `hf-mirror.com` for faster downloads.

### Manual Download

```bash
# Create models directory
mkdir -p /data/models

# Download using Chinese mirror
wget -O /data/models/boltz1.ckpt \
  "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/boltz1.ckpt"

wget -O /data/models/ccd.pkl \
  "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/ccd.pkl"
```

## Docker Compose

For multi-service deployment, use the provided `docker-compose.yml`:

```bash
docker-compose up -d
```

This starts:
- Inference service (port 50051)
- MSA service (port 50052)
- Training service (port 50053)
- Redis (for job queue)
- Prometheus & Grafana (monitoring)

## Health Check

The container includes a built-in health check:

```bash
# Check container health
docker inspect --format='{{.State.Health.Status}}' boltz-service

# Manual health check
docker exec boltz-service python3 -c "
import grpc
channel = grpc.insecure_channel('localhost:50051')
grpc.channel_ready_future(channel).result(timeout=5)
print('Service is healthy!')
"
```

## Troubleshooting

### GPU Not Detected

Ensure NVIDIA Docker runtime is installed:

```bash
sudo apt-get install nvidia-docker2
sudo systemctl restart docker
```

### Out of Memory

Reduce batch size or use a GPU with more memory:

```bash
docker run --gpus '"device=0"' \
  --shm-size=16g \
  -e NUM_WORKERS=1 \
  xingqiangchen/boltz-service:latest
```

### Slow Model Download

Use the Chinese HuggingFace mirror:

```bash
docker run -e HF_ENDPOINT=https://hf-mirror.com \
  xingqiangchen/boltz-service:latest-slim
```
