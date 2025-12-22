# Boltz Service API Reference

This document describes the gRPC API for the Boltz protein structure prediction service.

## Table of Contents

- [Overview](#overview)
- [Services](#services)
  - [Inference Service](#inference-service)
  - [MSA Service](#msa-service)
  - [Training Service](#training-service)
- [Common Types](#common-types)
- [Error Handling](#error-handling)
- [Examples](#examples)

## Overview

Boltz Service exposes three gRPC services:

| Service | Port | Description |
|---------|------|-------------|
| InferenceService | 50051 | Protein structure prediction |
| MSAService | 50053 | Multiple Sequence Alignment generation |
| TrainingService | 50052 | Model training management |

## Services

### Inference Service

The Inference Service handles protein structure prediction requests.

#### PredictStructure

Predict protein structure from amino acid sequence.

**Request: `PredictionRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `sequence` | string | Amino acid sequence (single-letter codes) |
| `recycling_steps` | int32 | Number of recycling steps (default: 3) |
| `sampling_steps` | int32 | Number of diffusion sampling steps (default: 200) |
| `diffusion_samples` | int32 | Number of structure samples to generate (default: 1) |
| `output_format` | string | Output format: "mmcif" or "pdb" |
| `model_version` | string | Model version to use (default: "latest") |

**Response: `PredictionResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Job status: "pending", "running", "completed", "failed" |
| `result_path` | string | Path to prediction result file |
| `error_message` | string | Error message if failed |

#### GetJobStatus

Get the status of a prediction job.

**Request: `JobStatusRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |

**Response: `JobStatusResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Current job status |
| `progress` | float | Progress percentage (0.0 - 1.0) |
| `result_path` | string | Path to result (if completed) |
| `error_message` | string | Error message (if failed) |

#### CancelJob

Cancel a running prediction job.

**Request: `CancelJobRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |

**Response: `CancelJobResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Final job status |

---

### MSA Service

The MSA Service generates Multiple Sequence Alignments for input sequences.

#### GenerateMSA

Generate MSA for a protein sequence using HHblits.

**Request: `MSARequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `sequence` | string | Input protein sequence |
| `max_seqs` | int32 | Maximum number of sequences (default: 1000) |
| `min_identity` | float | Minimum sequence identity (0.0 - 1.0, default: 0.3) |
| `num_iterations` | int32 | Number of HHblits iterations (default: 3) |

**Response: `MSAResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Job status |
| `result_path` | string | Path to MSA file (A3M format) |
| `error_message` | string | Error message if failed |

---

### Training Service

The Training Service manages model training jobs.

#### StartTraining

Start a new training job.

**Request: `TrainingRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Unique job identifier |
| `config_path` | string | Path to training configuration file |
| `args` | repeated string | Additional command-line arguments |
| `num_gpus` | int32 | Number of GPUs to use |
| `output_dir` | string | Output directory for checkpoints |
| `resume` | bool | Whether to resume from checkpoint |
| `checkpoint` | string | Path to checkpoint (if resuming) |
| `experiment_name` | string | Experiment name for logging |
| `hyperparameters` | map<string, string> | Training hyperparameters |

**Response: `TrainingResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Job status |
| `error_message` | string | Error message if failed |

#### GetTrainingStatus

Get detailed training job status.

**Request: `JobStatusRequest`**

**Response: `TrainingJobStatusResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `base` | JobStatusResponse | Base status information |
| `current_epoch` | float | Current training epoch |
| `val_loss` | float | Validation loss |
| `train_loss` | float | Training loss |
| `checkpoint_path` | string | Path to best checkpoint |
| `error_message` | string | Error message if failed |

#### ExportModel

Export a trained model to a deployable format.

**Request: `ExportModelRequest`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Training job identifier |
| `output_path` | string | Output path for exported model |
| `format` | string | Export format: "onnx" or "torchscript" |

**Response: `ExportModelResponse`**

| Field | Type | Description |
|-------|------|-------------|
| `job_id` | string | Job identifier |
| `status` | string | Export status |
| `model_path` | string | Path to exported model |
| `error_message` | string | Error message if failed |

---

## Common Types

### JobStatusRequest

```protobuf
message JobStatusRequest {
  string job_id = 1;
}
```

### JobStatusResponse

```protobuf
message JobStatusResponse {
  string job_id = 1;
  string status = 2;
  float progress = 3;
  string result_path = 4;
  string error_message = 5;
}
```

### CancelJobRequest

```protobuf
message CancelJobRequest {
  string job_id = 1;
}
```

### CancelJobResponse

```protobuf
message CancelJobResponse {
  string job_id = 1;
  string status = 2;
}
```

---

## Error Handling

The service uses standard gRPC status codes:

| Code | Description |
|------|-------------|
| `OK` | Request succeeded |
| `INVALID_ARGUMENT` | Invalid request parameters |
| `NOT_FOUND` | Requested resource not found |
| `ALREADY_EXISTS` | Resource already exists |
| `FAILED_PRECONDITION` | Operation preconditions not met |
| `INTERNAL` | Internal server error |
| `UNAVAILABLE` | Service temporarily unavailable |

---

## Examples

### Python Client Example

```python
import grpc
from boltz_service.protos import inference_service_pb2, inference_service_pb2_grpc

# Connect to the service
channel = grpc.insecure_channel('localhost:50051')
stub = inference_service_pb2_grpc.InferenceServiceStub(channel)

# Make a prediction request
request = inference_service_pb2.PredictionRequest(
    job_id="my-prediction-001",
    sequence="MVKVGVNGFGRIGRLVTRAAFNSGKVDIVAINDPFIDLNYMVYMFQYDSTHGKFHGTVKAENGKLVINGNPITIFQERDPSKIKWGDAGAEYVVESTGVFTTMEKAGAHLQGGAKRVIISAPSADAPMFVMGVNHEKYDNSLKIISNASCTTNCLAPLAKVIHDNFGIVEGLMTTVHAITATQKTVDGPSGKLWRDGRGALQNIIPASTGAAKAVGKVIPELNGKLTGMAFRVPTANVSVVDLTCRLEKPAKYDDIKKVVKQASEGPLKGILGYTEHQVVSSDFNSDTHSSTFDAGAGIALNDHFVKLISWYDNEFGYSNRVVDLMAHMASKE",
    recycling_steps=3,
    sampling_steps=200,
    diffusion_samples=1,
    output_format="mmcif",
    model_version="latest"
)

# Get response
response = stub.PredictStructure(request)
print(f"Job ID: {response.job_id}")
print(f"Status: {response.status}")
print(f"Result: {response.result_path}")
```

### Health Check Example

```python
from grpc_health.v1 import health_pb2, health_pb2_grpc

channel = grpc.insecure_channel('localhost:50051')
health_stub = health_pb2_grpc.HealthStub(channel)

request = health_pb2.HealthCheckRequest()
response = health_stub.Check(request)
print(f"Service status: {response.status}")
```

---

## Service Discovery

Services support gRPC reflection for service discovery:

```bash
# List available services
grpcurl -plaintext localhost:50051 list

# Describe a service
grpcurl -plaintext localhost:50051 describe boltz.InferenceService
```
