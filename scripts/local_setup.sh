#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Setting up local development environment for Boltz Service...${NC}"

# Check if Python virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt
pip install -e .

# Check if minikube is installed
if ! command -v minikube &> /dev/null; then
    echo -e "${YELLOW}Minikube not found. Please install minikube first:${NC}"
    echo "brew install minikube"
    exit 1
fi

# Check if minikube is running
if ! minikube status | grep -q "Running"; then
    echo -e "${YELLOW}Starting minikube...${NC}"
    minikube start
fi

# Set docker env to use minikube's docker daemon
echo -e "${YELLOW}Setting docker environment to minikube...${NC}"
eval $(minikube docker-env)

# Build docker image
echo -e "${YELLOW}Building docker image...${NC}"
docker build -t boltz-service:latest .

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
export BOLTZ_NAMESPACE="default"
pytest tests/ -v

echo -e "${GREEN}Setup complete! Your local environment is ready.${NC}"
echo -e "${GREEN}To deploy to local kubernetes cluster:${NC}"
echo -e "kubectl apply -f k8s/local/"
