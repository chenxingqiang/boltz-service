#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CLUSTER_NAME="${KIND_CLUSTER_NAME:-boltz-service}"
IMAGE_NAME="${BOLTZ_IMAGE:-boltz-service:local}"
NAMESPACE="boltz"
K8S_PROVIDER="${K8S_PROVIDER:-auto}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${YELLOW}$*${NC}"; }
ok() { echo -e "${GREEN}$*${NC}"; }
err() { echo -e "${RED}$*${NC}" >&2; }

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || { err "Missing required command: $1"; exit 1; }
}

need_cmd docker
need_cmd kubectl

cd "$ROOT_DIR"

detect_provider() {
  if [[ "$K8S_PROVIDER" != "auto" ]]; then
    echo "$K8S_PROVIDER"
    return
  fi
  if kubectl config current-context 2>/dev/null | grep -q '^minikube$'; then
    echo minikube
    return
  fi
  if kind get clusters 2>/dev/null | grep -qx "$CLUSTER_NAME"; then
    echo kind
    return
  fi
  if command -v kind >/dev/null 2>&1; then
    echo kind
    return
  fi
  if command -v minikube >/dev/null 2>&1; then
    echo minikube
    return
  fi
  err "No supported local Kubernetes provider found (kind/minikube)"
  exit 1
}

PROVIDER="$(detect_provider)"
log "Using Kubernetes provider: $PROVIDER"

if [[ "$PROVIDER" == "kind" ]]; then
  need_cmd kind
  if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
    log "Creating kind cluster: $CLUSTER_NAME"
    kind create cluster --name "$CLUSTER_NAME" --wait 180s
  fi
  kubectl cluster-info --context "kind-${CLUSTER_NAME}"
elif [[ "$PROVIDER" == "minikube" ]]; then
  need_cmd minikube
  if ! minikube status >/dev/null 2>&1; then
    log "Starting minikube"
    minikube start --driver=docker --cpus=2 --memory=1800
  fi
  eval "$(minikube docker-env)"
  kubectl cluster-info
fi

log "Building local image: $IMAGE_NAME"
docker build -f docker/Dockerfile.local -t "$IMAGE_NAME" .

if [[ "$PROVIDER" == "kind" ]]; then
  log "Loading image into kind"
  kind load docker-image "$IMAGE_NAME" --name "$CLUSTER_NAME"
fi

log "Applying Kubernetes manifests"
kubectl apply -f k8s/local/namespace.yaml
kubectl apply -f k8s/local/configmap.yaml
kubectl apply -f k8s/local/deployment.yaml
kubectl apply -f k8s/local/service.yaml

log "Waiting for deployment rollout"
kubectl rollout status deployment/boltz-service -n "$NAMESPACE" --timeout=900s

ok "Deployment ready"
kubectl get pods,svc -n "$NAMESPACE" -o wide

NODE_PORT=$(kubectl get svc boltz-service -n "$NAMESPACE" -o jsonpath='{.spec.ports[0].nodePort}')
MINIKUBE_IP=$(minikube ip 2>/dev/null || true)
if [[ -n "$MINIKUBE_IP" ]]; then
  ok "gRPC endpoint: ${MINIKUBE_IP}:${NODE_PORT}"
fi
ok "Port-forward: kubectl port-forward -n ${NAMESPACE} svc/boltz-service 50051:50051"
