# Boltz MSA Service Docker Deployment Guide

This guide provides detailed instructions for deploying the Boltz MSA (Multiple Sequence Alignment) service using Docker. The service includes HH-suite3 for sequence alignment and supports the BFD (Big Fantastic Database) for improved alignment quality.

## Table of Contents
- [Prerequisites](#prerequisites)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Detailed Setup](#detailed-setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

## Prerequisites

- Docker Engine (version 20.10.0 or later)
- Docker Compose (version 2.0.0 or later)
- At least 500GB free disk space for BFD database
- Minimum 16GB RAM
- Fast internet connection for database download

## System Requirements

### Minimum Requirements
- CPU: 4 cores
- RAM: 16GB
- Storage: 500GB free space
- Network: 1Gbps

### Recommended Requirements
- CPU: 8+ cores
- RAM: 32GB
- Storage: 1TB SSD
- Network: 10Gbps

## Quick Start

1. Clone the repository:
```bash
git clone https://github.com/your-org/boltz-service.git
cd boltz-service
```

2. Start the service:
```bash
docker-compose -f docker/msa/docker-compose.yml up -d
```

3. Download BFD database:
```bash
./docker/msa/prepare_bfd.sh
```

4. Verify the service is running:
```bash
docker-compose -f docker/msa/docker-compose.yml ps
```

## Detailed Setup

### 1. Directory Structure
```
docker/msa/
├── Dockerfile          # Multi-stage build for MSA service
├── docker-compose.yml  # Compose file for deployment
├── prepare_bfd.sh      # BFD database download script
└── README.md          # This documentation
```

### 2. Building the Docker Image

The Dockerfile uses a multi-stage build process:
- Stage 1: Builds HH-suite3 and installs Python dependencies
- Stage 2: Creates the runtime environment with minimal footprint

Build the image manually:
```bash
docker build -t boltz-msa -f docker/msa/Dockerfile .
```

### 3. Database Setup

The BFD database is essential for high-quality sequence alignments. Set it up using:

```bash
# Create Docker volumes
docker-compose -f docker/msa/docker-compose.yml up -d

# Download BFD database (this will take several hours)
./docker/msa/prepare_bfd.sh

# Verify database installation
docker exec boltz-msa ls -lh /data/bfd
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| BOLTZ_BFD_PATH | /data/bfd | Path to BFD database |
| BOLTZ_CACHE_DIR | /data/cache | Path to cache directory |

### Docker Compose Configuration

The `docker-compose.yml` file provides several configuration options:

```yaml
services:
  msa:
    deploy:
      resources:
        limits:
          memory: 16G        # Maximum memory usage
        reservations:
          memory: 8G         # Minimum memory reservation
```

### Volume Configuration

Two persistent volumes are used:
- `bfd_data`: Stores the BFD database
- `cache_data`: Stores MSA results cache

## Usage

### Starting the Service

```bash
docker-compose -f docker/msa/docker-compose.yml up -d
```

### Stopping the Service

```bash
docker-compose -f docker/msa/docker-compose.yml down
```

### Viewing Logs

```bash
docker-compose -f docker/msa/docker-compose.yml logs -f msa
```

### Making gRPC Calls

The service exposes the following gRPC endpoints on port 50053:

1. Generate MSA:
```python
import grpc
from boltz_service.protos import msa_pb2, msa_pb2_grpc

channel = grpc.insecure_channel('localhost:50053')
stub = msa_pb2_grpc.MSAServiceStub(channel)

request = msa_pb2.MSARequest(
    sequence="MVKVGVNG...",  # Your protein sequence
    max_sequences=2000
)

response = stub.GenerateMSA(request)
```

2. Check Job Status:
```python
status_request = common_pb2.JobStatusRequest(job_id=response.job_id)
status = stub.GetJobStatus(status_request)
```

## Monitoring

### Health Checks

The service includes built-in health checks:
```bash
# Check service health
docker-compose -f docker/msa/docker-compose.yml ps
```

### Resource Usage

Monitor resource usage:
```bash
docker stats boltz-msa
```

### Cache Management

The service automatically manages its cache, but you can manually clear it:
```bash
docker exec boltz-msa rm -rf /data/cache/*
```

## Troubleshooting

### Common Issues

1. **Service Won't Start**
   - Check system resources: `docker stats`
   - Verify BFD database: `docker exec boltz-msa ls -lh /data/bfd`
   - Check logs: `docker-compose logs msa`

2. **Out of Memory**
   - Increase memory limits in `docker-compose.yml`
   - Check for memory leaks: `docker stats`

3. **Slow Performance**
   - Verify BFD database is properly mounted
   - Check disk I/O: `iostat -x 1`
   - Monitor CPU usage: `top`

### Log Locations

- Container logs: `docker-compose logs msa`
- Application logs: Inside container at `/app/logs`

## Advanced Configuration

### Custom Database Path

To use a custom BFD database location:

1. Update docker-compose.yml:
```yaml
services:
  msa:
    volumes:
      - /path/to/your/bfd:/data/bfd
```

2. Set environment variable:
```yaml
    environment:
      - BOLTZ_BFD_PATH=/data/bfd
```

### Performance Tuning

For better performance:

1. Use SSD storage for volumes
2. Increase CPU allocation
3. Adjust memory limits based on workload
4. Enable database caching

### Security

The service runs as non-root user `boltz` inside the container. Additional security measures:

1. Regular security updates:
```bash
docker-compose pull
docker-compose up -d
```

2. Monitor container security:
```bash
docker scan boltz-msa
```
