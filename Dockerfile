FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    BOLTZ_CACHE_DIR=/data/cache \
    BOLTZ_MODEL_DIR=/data/models \
    REDIS_HOST=host.docker.internal \
    REDIS_PORT=6379 \
    REDIS_DB=0 \
    DEBUG=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        git \
        protobuf-compiler \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install --no-cache-dir \
        protobuf==4.21.6 \
        grpcio==1.54.2 \
        grpcio-tools==1.54.2 \
        grpcio-health-checking==1.54.2 \
        grpcio-reflection==1.54.2 \
        redis==5.0.3

WORKDIR /app/src/boltz_service/protos
RUN python -m grpc_tools.protoc \
        --proto_path=. \
        --python_out=. \
        --grpc_python_out=. \
        common.proto inference_service.proto msa_service.proto training_service.proto

RUN for f in *_pb2*.py; do \
        if [ -f "$f" ]; then \
            sed 's/import \([a-z_]*\)_pb2/from . import \1_pb2/g' "$f" > "$f.tmp" && \
            mv "$f.tmp" "$f"; \
        fi; \
    done

WORKDIR /app
RUN pip install -e .

RUN mkdir -p /data/cache /data/models

EXPOSE 50051

CMD ["python", "-m", "boltz_service.main", "serve", "--host", "0.0.0.0", "--port", "50051"]
