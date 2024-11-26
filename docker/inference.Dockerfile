# 使用NVIDIA CUDA基础镜像
FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.9 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# 安装HHblits和其他依赖
RUN apt-get update && apt-get install -y \
    hhsuite \
    wget \
    aria2 \
    && rm -rf /var/lib/apt/lists/*

# 下载BFD数据库
ENV BOLTZ_BFD_PATH=/data/bfd
RUN mkdir -p /data/bfd \
    && cd /data/bfd \
    && aria2c -x 16 https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz \
    && tar xzf bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz \
    && rm bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz

# 复制项目文件
COPY . /app/

# 安装Python依赖
RUN pip3 install --no-cache-dir -e .

# 创建必要的目录
RUN mkdir -p /app/models /app/cache /app/output

# 设置环境变量
ENV MODEL_PATH=/app/models
ENV CACHE_PATH=/app/cache
ENV OUTPUT_PATH=/app/output
ENV PYTHONPATH=/app
ENV BOLTZ_CACHE_DIR=/data/cache
ENV BOLTZ_TAXONOMY_PATH=/data/taxonomy.db

# 设置默认预测参数
ENV DEFAULT_DEVICES=1
ENV DEFAULT_ACCELERATOR=gpu
ENV DEFAULT_RECYCLING_STEPS=3
ENV DEFAULT_SAMPLING_STEPS=200
ENV DEFAULT_DIFFUSION_SAMPLES=1
ENV DEFAULT_OUTPUT_FORMAT=mmcif
ENV DEFAULT_NUM_WORKERS=2

# 暴露gRPC端口
EXPOSE 50051

RUN cd /app/models && \
    wget https://huggingface.co/boltz-community/boltz-1/resolve/main/boltz1.ckpt && \
    cd /app/cache && \
    wget https://huggingface.co/boltz-community/boltz-1/resolve/main/ccd.pkl


# 启动推理服务
CMD ["python3", "-m", "src.boltz_service.services.inference", "--port", "50051", \
     "--cache", "${CACHE_PATH}", \
     "--model_path", "${MODEL_PATH}", \
     "--output_path", "${OUTPUT_PATH}", \
     "--devices", "${DEFAULT_DEVICES}", \
     "--accelerator", "${DEFAULT_ACCELERATOR}", \
     "--recycling_steps", "${DEFAULT_RECYCLING_STEPS}", \
     "--sampling_steps", "${DEFAULT_SAMPLING_STEPS}", \
     "--diffusion_samples", "${DEFAULT_DIFFUSION_SAMPLES}", \
     "--output_format", "${DEFAULT_OUTPUT_FORMAT}", \
     "--num_workers", "${DEFAULT_NUM_WORKERS}"]
