# Boltz Service Kubernetes Testing

## Overview
This test suite provides comprehensive validation of Kubernetes deployments for the Boltz service, with advanced error handling and detailed logging.

## Prerequisites
- Python 3.11+
- Kubernetes cluster access
- Local or in-cluster kubeconfig

## Dependencies
Install required dependencies:
```bash
pip install -r requirements-k8s.txt
```

## Test Coverage
The test suite covers:
- Kubernetes cluster connectivity
- Deployment configuration
- Service validation
- Pod status monitoring
- Network connectivity
- Security context verification
- Resource requirement checks

## Error Handling
The test suite implements advanced error handling with:
- Custom exception classes
- Detailed logging
- Comprehensive error context
- Graceful failure mechanisms

### Exception Types
- `BoltzK8sTestError`: Base exception for all Kubernetes testing errors
- `K8sConnectivityError`: Connectivity-related failures
- `DeploymentConfigError`: Deployment and configuration issues
- `NetworkConnectivityError`: Inter-pod network problems

## Logging
Logging is configured to provide detailed insights:
- Timestamp
- Log level
- Detailed error messages
- Optional stack trace for debugging

## Running Tests
```bash
# Set namespace (optional)
export BOLTZ_NAMESPACE=default

# Run tests
pytest test_k8s_deployment.py -v
```

### Test Execution Options
- `-v`: Verbose output
- `--log-cli-level=INFO`: Show detailed logging
- `--timeout=300`: Set global test timeout

## Troubleshooting
1. Ensure Kubernetes client is installed
2. Verify cluster connectivity
3. Check kubeconfig permissions
4. Review detailed log output

## Security Considerations
- Non-root container execution
- Minimal privilege principle
- Read-only root filesystem preference

## Continuous Integration
These tests are designed to integrate with CI/CD pipelines, providing robust Kubernetes deployment validation.
