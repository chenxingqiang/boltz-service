"""Integration tests for the Boltz gRPC server."""

from pathlib import Path

from grpc_health.v1 import health_pb2, health_pb2_grpc
import grpc

from boltz_service.protos import (
    common_pb2,
    inference_service_pb2,
    msa_service_pb2,
    training_service_pb2,
)
TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_PORT = 50052


def test_inference_service(inference_stub):
    request = inference_service_pb2.PredictionRequest(
        job_id="test_inference_job",
        sequence="MVKVGVNG",
        recycling_steps=1,
        sampling_steps=10,
        diffusion_samples=1,
        output_format="pdb",
    )

    response = inference_stub.PredictStructure(request)

    assert response.status == "completed"
    assert response.job_id == "test_inference_job"
    assert response.result_path
    assert Path(response.result_path).exists()
    assert not response.error_message


def test_msa_service(msa_stub):
    request = msa_service_pb2.MSARequest(
        job_id="test_msa_job",
        sequence="MVKVGVNG",
        max_seqs=10,
        min_identity=0.3,
        num_iterations=3,
    )

    response = msa_stub.GenerateMSA(request)

    assert response.status == "completed"
    assert response.job_id == "test_msa_job"
    assert response.result_path
    assert Path(response.result_path).exists()
    assert not response.error_message


def test_training_service(training_stub):
    config_file = TEST_DATA_DIR / "test_config.yaml"
    config_file.write_text(
        """
version: 1
model:
  name: test_model
  hidden_size: 32
  num_layers: 2
training:
  batch_size: 2
  max_epochs: 1
  learning_rate: 0.001
""".strip(),
        encoding="utf-8",
    )

    request = training_service_pb2.TrainingRequest(
        job_id="test_job",
        config_path=str(config_file),
        num_gpus=1,
        output_dir=str(TEST_DATA_DIR / "output"),
        experiment_name="test_experiment",
        hyperparameters={
            "batch_size": "2",
            "max_epochs": "1",
        },
    )

    response = training_stub.StartTraining(request)

    assert response.status == "started"
    assert response.job_id == "test_job"
    assert not response.error_message


def test_health_check(grpc_server):
    del grpc_server
    channel = grpc.insecure_channel(f"127.0.0.1:{TEST_PORT}")
    health_stub = health_pb2_grpc.HealthStub(channel)

    response = health_stub.Check(health_pb2.HealthCheckRequest())

    assert response.status == health_pb2.HealthCheckResponse.SERVING


def test_inference_job_status(inference_stub):
    request = inference_service_pb2.PredictionRequest(
        job_id="status_job",
        sequence="MVKVGVNG",
        recycling_steps=1,
        sampling_steps=5,
        diffusion_samples=1,
        output_format="pdb",
    )
    inference_stub.PredictStructure(request)

    status = inference_stub.GetJobStatus(common_pb2.JobStatusRequest(job_id="status_job"))

    assert status.job_id == "status_job"
    assert status.status == "completed"
    assert status.progress == 1.0
    assert status.result_path
