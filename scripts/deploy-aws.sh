#!/bin/bash

# Exit on error
set -e

# Check required environment variables
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_REGION" ]; then
    echo "Error: AWS credentials not set. Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_REGION"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names boltz-service || \
    aws ecr create-repository --repository-name boltz-service

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Docker image
docker build -t boltz-service .
docker tag boltz-service:latest $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/boltz-service:latest
docker push $AWS_ACCOUNT.dkr.ecr.$AWS_REGION.amazonaws.com/boltz-service:latest

# Update Kubernetes configs with AWS account and region
sed -i '' "s/\${AWS_ACCOUNT}/$AWS_ACCOUNT/g" k8s/aws/deployment.yaml
sed -i '' "s/\${AWS_REGION}/$AWS_REGION/g" k8s/aws/deployment.yaml
sed -i '' "s/\${AWS_REGION}/$AWS_REGION/g" k8s/aws/config.yaml
sed -i '' "s/\${AWS_ACCESS_KEY_ID}/$AWS_ACCESS_KEY_ID/g" k8s/aws/config.yaml
sed -i '' "s/\${AWS_SECRET_ACCESS_KEY}/$AWS_SECRET_ACCESS_KEY/g" k8s/aws/config.yaml

# Apply Kubernetes configurations
kubectl apply -f k8s/aws/config.yaml
kubectl apply -f k8s/aws/deployment.yaml

# Wait for deployment
kubectl rollout status deployment/boltz-service

echo "Deployment completed successfully!"
echo "Service endpoint: $(kubectl get service boltz-service -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')"
