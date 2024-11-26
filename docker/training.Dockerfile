# 使用NVIDIA CUDA基础镜像,训练需要完整的CUDA工具链
# Build stage
FROM nvidia/cuda:12.1.0-devel-ubuntu22.04 as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3-pip \
    git \
    && rm -rf /var/lib/apt/lists/*

# 创建和激活虚拟环境
RUN python3.10 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip3 install --no-cache-dir -e .

# Runtime stage
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    && rm -rf /var/lib/apt/lists/*

# 复制虚拟环境从builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用程序代码
COPY --from=builder /app /app

# 创建必要的目录
RUN mkdir -p /app/data /app/checkpoints /app/models

# 设置环境变量
ENV DATA_PATH=/app/data \
    CHECKPOINT_PATH=/app/checkpoints \
    MODEL_PATH=/app/models \
    PYTHONPATH=/app \
    WANDB_SILENT=true

# 暴露gRPC端口
EXPOSE 50052


# Download model and CCD files from HuggingFace
RUN cd /app/models && \
    wget https://huggingface.co/boltz-community/boltz-1/resolve/main/boltz1.ckpt && \
    cd /app/cache && \
    wget https://huggingface.co/boltz-community/boltz-1/resolve/main/ccd.pkl

# 启动训练服务
CMD ["python3", "-m", "src.boltz_service.services.training", "--port", "50052"]
