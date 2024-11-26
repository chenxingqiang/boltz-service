# Boltz MSA Service Kubernetes Deployment Guide

This guide provides instructions for deploying the Boltz MSA (Multiple Sequence Alignment) service on Kubernetes.

## Prerequisites

- Kubernetes cluster (v1.20+)
- kubectl configured to access your cluster
- Storage class that supports ReadWriteOnce volumes
- At least 500GB available storage
- Nodes with minimum 16GB RAM

## Directory Structure

```
k8s/msa/
├── namespace.yaml         # Boltz namespace
├── configmap.yaml        # Service configuration
├── scripts-configmap.yaml # Download scripts
├── storage.yaml         # PVC definitions
├── service.yaml         # Service definition
├── statefulset.yaml     # StatefulSet for MSA service
├── init-job.yaml        # BFD database download job
└── README.md           # This documentation
```

## Deployment Steps

1. Create namespace and configurations:
```bash
kubectl apply -f k8s/msa/namespace.yaml
kubectl apply -f k8s/msa/configmap.yaml
kubectl apply -f k8s/msa/scripts-configmap.yaml
```

2. Create storage:
```bash
kubectl apply -f k8s/msa/storage.yaml
```

3. Download BFD database:
```bash
kubectl apply -f k8s/msa/init-job.yaml
```

Monitor download progress:
```bash
kubectl -n boltz logs -f job/bfd-download
```

4. Deploy the service:
```bash
kubectl apply -f k8s/msa/service.yaml
kubectl apply -f k8s/msa/statefulset.yaml
```

## Monitoring

Check service status:
```bash
kubectl -n boltz get pods
kubectl -n boltz get statefulset msa
```

View logs:
```bash
kubectl -n boltz logs -f statefulset/msa
```

Check storage:
```bash
kubectl -n boltz get pvc
```

## Configuration

### Resource Limits

The service is configured with the following resource limits:
- Memory: 8-16GB
- CPU: 2-4 cores

Adjust these in `statefulset.yaml` based on your needs:
```yaml
resources:
  requests:
    memory: "8Gi"
    cpu: "2"
  limits:
    memory: "16Gi"
    cpu: "4"
```

### Storage

Two PVCs are created:
- `bfd-data`: 500GB for BFD database
- `cache-data`: 100GB for MSA cache

Modify sizes in `storage.yaml` if needed.

### Environment Variables

Configure via `configmap.yaml`:
- `BOLTZ_BFD_PATH`: Path to BFD database
- `BOLTZ_CACHE_DIR`: Path to cache directory

## Accessing the Service

The service is exposed internally at `msa-service.boltz.svc.cluster.local:50053`.

Example gRPC client configuration:
```python
import grpc
from boltz_service.protos import msa_pb2, msa_pb2_grpc

channel = grpc.insecure_channel('msa-service.boltz.svc.cluster.local:50053')
stub = msa_pb2_grpc.MSAServiceStub(channel)
```

## Troubleshooting

1. **Pod won't start**:
```bash
kubectl -n boltz describe pod msa-0
kubectl -n boltz get events
```

2. **Storage issues**:
```bash
kubectl -n boltz describe pvc bfd-data
kubectl -n boltz describe pvc cache-data
```

3. **Service unreachable**:
```bash
kubectl -n boltz get endpoints msa-service
kubectl -n boltz describe service msa-service
```

## Maintenance

### Updating the Service

1. Update image:
```bash
kubectl -n boltz set image statefulset/msa msa=boltz-msa:new-version
```

2. Rolling restart:
```bash
kubectl -n boltz rollout restart statefulset msa
```

### Backup

Backup PVC data:
```bash
kubectl -n boltz exec msa-0 -- tar czf /tmp/bfd-backup.tar.gz /data/bfd
kubectl -n boltz cp msa-0:/tmp/bfd-backup.tar.gz ./bfd-backup.tar.gz
```

## Security

The service runs as non-root user (UID 1000) and includes:
- Read-only root filesystem
- No privileged access
- Resource limits
- Network policy (optional)

## Scaling

The service uses StatefulSet with:
- Single replica (default)
- Persistent storage
- Stable network identity

Note: Multiple replicas are not recommended due to the large database size.
