# Stage 1: Build environment
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    cmake \
    wget \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Build HH-suite3 from source
RUN git clone --depth 1 https://github.com/soedinglab/hh-suite.git /tmp/hh-suite \
    && cd /tmp/hh-suite \
    && mkdir build \
    && cd build \
    && cmake -DCMAKE_INSTALL_PREFIX=/opt/hhsuite .. \
    && make -j$(nproc) \
    && make install \
    && cd / \
    && rm -rf /tmp/hh-suite

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY setup.py requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy HH-suite binaries and libraries
COPY --from=builder /opt/hhsuite /usr/local/
ENV PATH="/usr/local/bin:$PATH" \
    LD_LIBRARY_PATH="/usr/local/lib:${LD_LIBRARY_PATH:-}"

# Copy virtual environment
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create directories for databases and cache
RUN mkdir -p /data/bfd /data/cache
ENV BOLTZ_BFD_PATH=/data/bfd \
    BOLTZ_CACHE_DIR=/data/cache

# Copy application code
COPY src/ /app/src/
COPY scripts/ /app/scripts/
WORKDIR /app

# Add the app directory to PYTHONPATH
ENV PYTHONPATH=/app:${PYTHONPATH}

# Create non-root user
RUN useradd -m -u 1000 boltz && \
    chown -R boltz:boltz /data /app
USER boltz

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD grpc_health_probe -addr=localhost:50053 || exit 1

# Expose gRPC port
EXPOSE 50053

# Start MSA service
CMD ["python", "-m", "src.boltz_service.services.msa", "--port", "50053"]
