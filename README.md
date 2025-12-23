# Boltz Service

[![GitHub](https://img.shields.io/github/license/chenxingqiang/boltz-service)](https://github.com/chenxingqiang/boltz-service/blob/main/LICENSE)
[![Docker Hub](https://img.shields.io/docker/pulls/xingqiangchen/boltz-service)](https://hub.docker.com/r/xingqiangchen/boltz-service)
[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-red)](https://pytorch.org/)

A high-performance protein structure prediction microservice with cloud-native deployment support. Supports both **Boltz-1** and **Boltz-2** models.

## Features

- State-of-the-art protein structure prediction
- Cloud deployment support (AWS & Aliyun)
- GPU acceleration
- Multiple Sequence Alignment (MSA) generation
- Comprehensive monitoring

## Installation

```bash
git clone https://github.com/chenxingqiang/boltz-service.git
cd boltz-service
pip install -r requirements.txt
```

## Quick Start

1. Set environment variables:
```bash
export BOLTZ_CACHE_DIR=/path/to/cache
export BOLTZ_MODEL_DIR=/path/to/models
export BOLTZ_BFD_PATH=/path/to/bfd
export BOLTZ_UNIREF_PATH=/path/to/uniref
```

2. Start the service:
```bash
python -m boltz.main serve \
    --host 0.0.0.0 \
    --port 50051 \
    --workers 10 \
    --cache ~/.boltz \
    --devices 1 \
    --accelerator gpu
```

## Roadmap

- [x] Basic protein structure prediction
- [x] MSA generation support
- [x] Cloud deployment (AWS/Aliyun)
- [x] GPU acceleration
- [-] Support for custom paired MSA
- [ ] Pocket conditioning support
- [ ] More examples
- [ ] Full data processing pipeline
- [ ] Colab notebook for inference
- [ ] Confidence model checkpoint
- [ ] Kernel integration

## License

Our model and code are released under MIT License, and can be freely used for both academic and commercial purposes.

## Links

- [GitHub Repository](https://github.com/chenxingqiang/boltz-service)
- [API Documentation](docs/API.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Issue Tracker](https://github.com/chenxingqiang/boltz-service/issues)

## Architecture

### MSA Service

The Multiple Sequence Alignment (MSA) service is a key component of the Boltz architecture, implemented as a gRPC-based microservice. It provides efficient sequence alignment capabilities with the following features:

- **Asynchronous Processing**: Handles long-running MSA tasks efficiently using asyncio
- **Distributed Caching**: Uses Redis for caching results and improving performance
- **Batch Processing**: Supports processing multiple sequences in parallel
- **Status Monitoring**: Real-time status updates for MSA generation tasks
- **Configurable Options**: Flexible configuration for sequence identity, iteration count, etc.

Key endpoints:
- `GenerateMSA`: Generate MSA for a single protein sequence
- `BatchGenerateMSA`: Process multiple sequences in batch
- `GetMSAStatus`: Check the status of MSA generation tasks

Default configuration:
- Max Sequences: 1000
- Sequence Identity Range: 30-90%
- Iteration Count: 3
- Supported Databases: BFD, UniRef90

### System Requirements

- Python 3.8 or higher
- Redis server (for MSA service caching)
- CUDA-compatible GPU (recommended for inference)

### Dependencies

Core dependencies:
```
grpcio>=1.54.2
grpcio-tools>=1.54.2
protobuf>=4.23.2
numpy>=1.21.0
torch>=2.0.0
```

For a complete list of dependencies, see `requirements.txt`.

## Service Deployment

### Local Deployment

Run the service locally:
```bash
python -m boltz.service.main
```

### Docker Deployment

#### Pre-built Images (Recommended)

Pull pre-built images from [Docker Hub](https://hub.docker.com/r/xingqiangchen/boltz-service):

| Tag | Model | Size | Description |
|-----|-------|------|-------------|
| `v1` / `boltz1` | Boltz-1 | ~15GB | Boltz-1 model with all dependencies |
| `v2` / `boltz2` | Boltz-2 | ~14GB | Boltz-2 model with affinity prediction |
| `latest` | Boltz-1 | ~15GB | Default (same as v1) |
| `latest-slim` | None | ~7.5GB | Downloads model on first run |

```bash
# Boltz-1 (recommended for general use)
docker pull xingqiangchen/boltz-service:v1

# Boltz-2 (with affinity prediction)
docker pull xingqiangchen/boltz-service:v2

# Slim version (downloads model on first run)
docker pull xingqiangchen/boltz-service:latest-slim
```

#### Run the Service

```bash
# Run Boltz-1 model
docker run -d --gpus all \
  -p 50051:50051 \
  --name boltz-service \
  xingqiangchen/boltz-service:v1

# Run Boltz-2 model
docker run -d --gpus all \
  -p 50051:50051 \
  --name boltz-service \
  xingqiangchen/boltz-service:v2

# Run slim version with external model
docker run -d --gpus all \
  -p 50051:50051 \
  -v /path/to/models:/data/models \
  --name boltz-service \
  xingqiangchen/boltz-service:latest-slim
```

For detailed Docker documentation, see [Docker Guide](docs/docker.md).

#### Build from Source

```bash
# Build Boltz-1 image
docker build -f docker/Dockerfile.boltz1 -t boltz-service:v1 .

# Build Boltz-2 image
docker build -f docker/Dockerfile.boltz2 -t boltz-service:v2 .

#### Docker Compose
For local development and testing, you can use Docker Compose to run all services:

```bash
docker-compose up -d
```

The services will be available at:
- Training Service: `localhost:50052`
- MSA Service: `localhost:50053`
- Inference Service: `localhost:50051`

#### Environment Variables

The following environment variables can be configured for the Docker containers:

```bash
# Common
PYTHONPATH=/app
WANDB_SILENT=true

# Training Service
DATA_PATH=/app/data
CHECKPOINT_PATH=/app/checkpoints
MODEL_PATH=/app/models

# MSA Service
BOLTZ_BFD_PATH=/data/bfd
BOLTZ_CACHE_DIR=/data/cache

# Inference Service
BOLTZ_MODEL_DIR=/app/models
```

#### GPU Support

All services support GPU acceleration. Make sure you have the NVIDIA Container Toolkit installed:
```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

Then run the containers with `--gpus all` flag as shown in the examples above.

### Cloud Deployment

#### AWS EKS Deployment
1. Create EKS cluster:
```bash
eksctl create cluster --name boltz-cluster --region your-region
```

2. Deploy the service:
```bash
kubectl apply -f k8s/aws/
```

#### AWS ECS Deployment
1. Create ECS cluster through AWS Console or CLI
2. Push Docker image to ECR:
```bash
aws ecr create-repository --repository-name boltz-service
aws ecr get-login-password | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com
docker tag boltz-service:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/boltz-service:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/boltz-service:latest
```

#### Aliyun Kubernetes Deployment
1. Deploy using the provided script:
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh
```

## Monitoring and Scaling

### AWS CloudWatch Integration
- Service metrics and logs are automatically sent to CloudWatch
- Set up alarms and dashboards through AWS Console
- Configure auto-scaling based on metrics

### Aliyun Monitoring
- Monitor through Aliyun Container Service console
- Configure auto-scaling policies
- View service logs and metrics

## API Reference

The service exposes a gRPC API for protein structure prediction:

```protobuf
service BoltzService {
  rpc PredictStructure(PredictRequest) returns (PredictResponse);
  rpc GenerateMSA(MSARequest) returns (MSAResponse);
}
```

For detailed API documentation, see [API Reference](docs/API.md).

### Quick API Example

```python
import grpc
from boltz_service.protos import inference_service_pb2, inference_service_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
stub = inference_service_pb2_grpc.InferenceServiceStub(channel)

request = inference_service_pb2.PredictionRequest(
    job_id="prediction-001",
    sequence="MVKVGVNG",
    recycling_steps=3,
    sampling_steps=200,
    output_format="mmcif"
)

response = stub.PredictStructure(request)
print(f"Status: {response.status}")
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details on:

- Development setup
- Coding standards
- Testing guidelines
- Pull request process

Quick start:
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## Citation

If you use this software in your research, please cite:

```bibtex
@software{boltz2023,
  author = {Chen, Xingqiang},
  title = {Boltz Service: High-Performance Protein Structure Prediction},
  year = {2024},
  publisher = {GitHub},
  url = {https://github.com/chenxingqiang/boltz-service}
}
```

## Acknowledgments

- [Boltz Team](https://github.com/jwohlwend/boltz) for their groundbreaking work on protein structure prediction:
  * [Giacomo Corso](https://github.com/gcorso)
  * [Jordan Wohlwend](https://github.com/jwohlwend)
  * [Bowen Jing](https://github.com/bowenjing)
  * [Bonnie Berger](https://people.csail.mit.edu/bab/)
  * Original Paper: [Democratizing Biomolecular Interaction Modeling](https://gcorso.github.io/assets/boltz1.pdf)
- [PyTorch](https://pytorch.org/) for the deep learning framework
- [HHblits](https://github.com/soedinglab/hh-suite) for MSA generation
- The protein structure prediction community for their research and contributions
