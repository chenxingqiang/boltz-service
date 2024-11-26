#!/bin/bash

# Exit on error
set -e

# Check required environment variables
if [ -z "$ALIYUN_ACCESS_KEY_ID" ] || [ -z "$ALIYUN_ACCESS_KEY_SECRET" ] || [ -z "$ALIYUN_REGION" ]; then
    echo "Error: Aliyun credentials not set. Please set ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, and ALIYUN_REGION"
    exit 1
fi

# Set default values if not provided
ALIYUN_NAMESPACE=${ALIYUN_NAMESPACE:-"default"}
ALIYUN_REGISTRY=${ALIYUN_REGISTRY:-"registry.${ALIYUN_REGION}.aliyuncs.com"}

echo "Using Aliyun Registry: ${ALIYUN_REGISTRY}"
echo "Using Namespace: ${ALIYUN_NAMESPACE}"

# Login to Aliyun container registry
echo "Logging in to Aliyun container registry..."
docker login --username=${ALIYUN_ACCESS_KEY_ID} --password=${ALIYUN_ACCESS_KEY_SECRET} ${ALIYUN_REGISTRY}

# Build and push Docker image
echo "Building Docker image..."
docker build -t boltz-service .
docker tag boltz-service:latest ${ALIYUN_REGISTRY}/${ALIYUN_NAMESPACE}/boltz-service:latest
echo "Pushing Docker image..."
docker push ${ALIYUN_REGISTRY}/${ALIYUN_NAMESPACE}/boltz-service:latest

# Update Kubernetes configs with Aliyun settings
echo "Updating Kubernetes configurations..."
for file in k8s/aliyun/*.yaml; do
    sed -i '' "s/\${ALIYUN_REGISTRY}/$ALIYUN_REGISTRY/g" "$file"
    sed -i '' "s/\${ALIYUN_NAMESPACE}/$ALIYUN_NAMESPACE/g" "$file"
    sed -i '' "s/\${ALIYUN_REGION}/$ALIYUN_REGION/g" "$file"
    sed -i '' "s/\${ALIYUN_ACCESS_KEY_ID}/$ALIYUN_ACCESS_KEY_ID/g" "$file"
    sed -i '' "s/\${ALIYUN_ACCESS_KEY_SECRET}/$ALIYUN_ACCESS_KEY_SECRET/g" "$file"
done

# Create namespace if it doesn't exist
echo "Creating namespace if it doesn't exist..."
kubectl create namespace ${ALIYUN_NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# Apply Kubernetes configurations
echo "Creating storage volumes..."
kubectl apply -f k8s/aliyun/storage.yaml -n ${ALIYUN_NAMESPACE}

echo "Applying configuration and secrets..."
kubectl apply -f k8s/aliyun/config.yaml -n ${ALIYUN_NAMESPACE}
kubectl apply -f k8s/aliyun/configmap.yaml -n ${ALIYUN_NAMESPACE}
kubectl apply -f k8s/aliyun/init-data-configmap.yaml -n ${ALIYUN_NAMESPACE}

echo "Initializing data (this may take a while)..."
kubectl apply -f k8s/aliyun/init-data-job.yaml -n ${ALIYUN_NAMESPACE}
kubectl wait --for=condition=complete job/boltz-data-init -n ${ALIYUN_NAMESPACE} --timeout=3600s

echo "Deploying service..."
kubectl apply -f k8s/aliyun/deployment.yaml -n ${ALIYUN_NAMESPACE}

# Wait for deployment
echo "Waiting for deployment to complete..."
kubectl rollout status deployment/boltz-service -n ${ALIYUN_NAMESPACE}

echo "Deployment completed successfully!"
echo "Service endpoint: $(kubectl get service boltz-service -n ${ALIYUN_NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')"

# Print some helpful information
echo -e "\nUseful commands:"
echo "  - Check pods status: kubectl get pods -n ${ALIYUN_NAMESPACE}"
echo "  - Check service status: kubectl get service boltz-service -n ${ALIYUN_NAMESPACE}"
echo "  - View pod logs: kubectl logs -f deployment/boltz-service -n ${ALIYUN_NAMESPACE}"
echo "  - Check data initialization job: kubectl get job boltz-data-init -n ${ALIYUN_NAMESPACE}"
