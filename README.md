# Boltz Service

[![GitHub](https://img.shields.io/github/license/chenxingqiang/boltz-service)](https://github.com/chenxingqiang/boltz-service/blob/main/LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-red)](https://pytorch.org/)

A high-performance protein structure prediction microservice with cloud-native deployment support.

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
- [Documentation](https://bolzt-service.repo.wiki)
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

The service is composed of multiple microservices that can be built and run using Docker:

#### Training Service
```bash
# Build the training service
docker build -f docker/training.Dockerfile -t boltz-training:latest .

# Run the training service
docker run -p 50052:50052 \
  -v /path/to/data:/app/data \
  -v /path/to/checkpoints:/app/checkpoints \
  -v /path/to/models:/app/models \
  --gpus all \
  boltz-training:latest
```

#### MSA Service
```bash
# Build the MSA service
docker build -f docker/msa/Dockerfile -t boltz-msa:latest .

# Run the MSA service
docker run -p 50053:50053 \
  -v /path/to/bfd:/data/bfd \
  -v /path/to/cache:/data/cache \
  boltz-msa:latest
```

#### Inference Service
```bash
# Build the inference service (for ARM64)
docker build -f docker/inference.arm64.Dockerfile -t boltz-inference:latest .
# Or for x86_64
docker build -f docker/inference.Dockerfile -t boltz-inference:latest .

# Run the inference service
docker run -p 50051:50051 \
  -v /path/to/models:/app/models \
  --gpus all \
  boltz-inference:latest
```

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

For detailed API documentation, see [API.md](docs/API.md).

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Citation

If you use this software in your research, please cite:

```bibtex
@software{boltz2023,
  author = {Boltz Labs},
  title = {Boltz Service: High-Performance Protein Structure Prediction},
  year = {2023},
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
