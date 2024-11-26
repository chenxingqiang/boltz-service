# Use Python base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src
ENV BOLTZ_CACHE_DIR=/data/cache
ENV BOLTZ_MODEL_DIR=/data/models
ENV REDIS_HOST=host.docker.internal
ENV REDIS_PORT=6379
ENV REDIS_DB=0
ENV DEBUG=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    protobuf-compiler \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source code and setup files
COPY . .

# Install gRPC dependencies first with compatible protobuf version
RUN pip install --no-cache-dir \
    protobuf==4.21.6 \
    grpcio==1.54.2 \
    grpcio-tools==1.54.2 \
    grpcio-health-checking==1.54.2 \
    grpcio-reflection==1.54.2 \
    redis==5.0.3

# Compile proto files
WORKDIR /app/src/boltz_service/protos
RUN python -m grpc_tools.protoc \
    --proto_path=. \
    --python_out=. \
    --grpc_python_out=. \
    common.proto inference_service.proto msa_service.proto training_service.proto

# Fix proto imports by creating a temporary file and moving it back
RUN for f in *_pb2*.py; do \
    if [ -f "$f" ]; then \
        sed 's/import \([a-z_]*\)_pb2/from . import \1_pb2/g' "$f" > "$f.tmp" && \
        mv "$f.tmp" "$f"; \
    fi \
done

# Return to app directory and install the package
WORKDIR /app
RUN pip install -e .

# Create necessary directories
RUN mkdir -p /data/cache /data/models

# Expose port
EXPOSE 50051

# Command to run the server
CMD ["python", "-m", "boltz_service.main"]
