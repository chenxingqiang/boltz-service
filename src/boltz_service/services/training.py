"""Boltz training service implementation."""

import logging
import os
from concurrent import futures
from typing import Dict, Optional
import json

import grpc
import torch
import pytorch_lightning as pl
from mashumaro import DataClassDictMixin
from dataclasses import dataclass
import wandb
from pathlib import Path

from boltz_service.data.module.training import BoltzTrainingDataModule
from boltz_service.model.model import BoltzModel

# Generated proto code
from boltz_service.protos import training_service_pb2
from boltz_service.protos import training_service_pb2_grpc
from boltz_service.protos import common_pb2
from boltz_service.data.types import ServiceConfig

logger = logging.getLogger(__name__)


@dataclass
class TrainingJob(DataClassDictMixin):
    """Training job dataclass."""

    job_id: str
    config_path: str
    args: list
    num_gpus: int
    output_dir: str
    resume: bool
    checkpoint: Optional[str]
    experiment_name: str
    hyperparameters: Dict[str, str]
    status: str = "pending"
    current_epoch: float = 0
    val_loss: float = float("inf")
    train_loss: float = float("inf")
    checkpoint_path: Optional[str] = None
    error_message: Optional[str] = None


class TrainingService(training_service_pb2_grpc.TrainingServiceServicer):
    """Training service implementation."""

    def __init__(self, config: ServiceConfig):
        """Initialize training service.

        Parameters
        ----------
        config : ServiceConfig
            Service configuration
        """
        self.data_path = config.data_path
        self.checkpoint_path = config.checkpoint_path
        self.model_path = config.model_path

        # Training job queue
        self.jobs: Dict[str, TrainingJob] = {}
        # Current running job
        self.current_job: Optional[str] = None

    def StartTraining(
        self,
        request: training_service_pb2.TrainingRequest,
        context: grpc.ServicerContext,
    ) -> training_service_pb2.TrainingResponse:
        """Start a training job.

        Parameters
        ----------
        request : TrainingRequest
            Training request containing job configuration
        context : grpc.ServicerContext
            gRPC context

        Returns
        -------
        TrainingResponse
            Response containing job status
        """
        # Check if job already exists
        if request.job_id in self.jobs:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"Job {request.job_id} already exists")
            return training_service_pb2.TrainingResponse(
                job_id=request.job_id,
                status="failed",
                error_message="Job already exists",
            )

        # Create job
        job = TrainingJob(
            job_id=request.job_id,
            config_path=request.config_path,
            args=request.args,
            num_gpus=request.num_gpus,
            output_dir=request.output_dir,
            resume=request.resume,
            checkpoint=request.checkpoint,
            experiment_name=request.experiment_name,
            hyperparameters=dict(request.hyperparameters),
        )
        self.jobs[job.job_id] = job

        # Execute training asynchronously
        future = self._train_async(job)
        future.add_done_callback(
            lambda f: self._handle_training_complete(job.job_id, f)
        )

        return training_service_pb2.TrainingResponse(
            job_id=job.job_id, status="started"
        )

    def GetTrainingStatus(
        self,
        request: common_pb2.JobStatusRequest,
        context: grpc.ServicerContext,
    ) -> training_service_pb2.TrainingJobStatusResponse:
        """Get training job status.

        Parameters
        ----------
        request : JobStatusRequest
            Request containing job ID
        context : grpc.ServicerContext
            gRPC context

        Returns
        -------
        TrainingJobStatusResponse
            Response containing training status
        """
        job = self.jobs.get(request.job_id)
        if not job:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Job {request.job_id} not found")
            return training_service_pb2.TrainingJobStatusResponse()

        # Build base status response
        base_status = common_pb2.JobStatusResponse(
            job_id=job.job_id, status=job.status, error_message=job.error_message
        )

        # Return training-specific status
        return training_service_pb2.TrainingJobStatusResponse(
            base=base_status,
            current_epoch=job.current_epoch,
            val_loss=job.val_loss,
            train_loss=job.train_loss,
            checkpoint_path=job.checkpoint_path,
            error_message=job.error_message,
        )

    def CancelJob(
        self,
        request: common_pb2.CancelJobRequest,
        context: grpc.ServicerContext,
    ) -> training_service_pb2.TrainingResponse:
        """Cancel a training job.

        Parameters
        ----------
        request : CancelJobRequest
            Request containing job ID to cancel
        context : grpc.ServicerContext
            gRPC context

        Returns
        -------
        TrainingResponse
            Response containing cancellation status
        """
        if not self.current_job or request.job_id != self.current_job:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No active job to cancel")
            return training_service_pb2.TrainingResponse(
                job_id=request.job_id,
                status="failed",
                error_message="No active job to cancel",
            )

        # Stop training
        job = self.jobs[request.job_id]
        job.status = "cancelled"

        return training_service_pb2.TrainingResponse(
            job_id=request.job_id, status="cancelled"
        )

    def ExportModel(
        self,
        request: training_service_pb2.ExportModelRequest,
        context: grpc.ServicerContext,
    ) -> training_service_pb2.ExportModelResponse:
        """Export a trained model.

        Parameters
        ----------
        request : ExportModelRequest
            Request containing export configuration
        context : grpc.ServicerContext
            gRPC context

        Returns
        -------
        ExportModelResponse
            Response containing export status and path
        """
        job = self.jobs.get(request.job_id)
        if not job:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Job {request.job_id} not found")
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id, status="not_found"
            )

        # Check if checkpoint exists
        if not job.checkpoint_path:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No checkpoint available")
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id,
                status="failed",
                error_message="No checkpoint available",
            )

        try:
            # Load model
            model = BoltzModel.load_from_checkpoint(job.checkpoint_path)

            # Export model
            output_path = Path(request.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Export based on format
            if request.format == "onnx":
                model.to_onnx(output_path)
            elif request.format == "torchscript":
                model.to_torchscript(output_path)
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unsupported format: {request.format}")
                return training_service_pb2.ExportModelResponse(
                    job_id=request.job_id,
                    status="failed",
                    error_message=f"Unsupported format: {request.format}",
                )

            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id, status="success", model_path=str(output_path)
            )

        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id, status="failed", error_message=str(e)
            )

    def _train_async(self, job: TrainingJob) -> futures.Future:
        """Execute training asynchronously.

        Parameters
        ----------
        job : TrainingJob
            Training job to execute

        Returns
        -------
        futures.Future
            Future for the training task
        """
        thread = futures.ThreadPoolExecutor(max_workers=1)
        future = thread.submit(self._train, job)
        return future

    def _train(self, job: TrainingJob):
        """Execute training.

        Parameters
        ----------
        job : TrainingJob
            Training job to execute
        """
        try:
            # Set current job
            self.current_job = job.job_id
            job.status = "running"

            # Initialize wandb
            wandb.init(
                project="boltz", name=job.experiment_name, config=job.hyperparameters
            )

            # Create data module
            datamodule = BoltzTrainingDataModule(cfg=job.hyperparameters)

            # Create or load model
            if job.resume and job.checkpoint:
                model = BoltzModel.load_from_checkpoint(
                    job.checkpoint, **job.hyperparameters
                )
            else:
                model = BoltzModel(**job.hyperparameters)

            # Create trainer
            trainer = pl.Trainer(
                default_root_dir=job.output_dir,
                devices=job.num_gpus,
                accelerator="gpu",
                callbacks=[self._create_status_callback(job)],
                **job.hyperparameters,
            )

            # Start training
            trainer.fit(model, datamodule)

            # Update status
            job.status = "completed"
            job.checkpoint_path = trainer.checkpoint_callback.best_model_path

        except Exception as e:
            logger.exception("Training failed")
            job.status = "failed"
            job.error_message = str(e)
            raise

        finally:
            # Clean up current job
            if self.current_job == job.job_id:
                self.current_job = None
            wandb.finish()

    def _create_status_callback(self, job: TrainingJob):
        """Create status update callback.

        Parameters
        ----------
        job : TrainingJob
            Training job to update

        Returns
        -------
        pl.Callback
            PyTorch Lightning callback for status updates
        """

        class StatusCallback(pl.Callback):
            def on_train_epoch_end(self, trainer, pl_module):
                job.current_epoch = trainer.current_epoch
                job.train_loss = float(
                    trainer.callback_metrics.get("train_loss", float("inf"))
                )
                job.val_loss = float(
                    trainer.callback_metrics.get("val_loss", float("inf"))
                )

            def on_exception(self, trainer, pl_module, exception):
                job.status = "failed"
                job.error_message = str(exception)

        return StatusCallback()

    def _handle_training_complete(self, job_id: str, future: futures.Future):
        """Handle training completion callback.

        Parameters
        ----------
        job_id : str
            Job identifier
        future : futures.Future
            Completed future
        """
        try:
            future.result()
        except Exception as e:
            logger.exception("Training failed")
            job = self.jobs.get(job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)


def serve(port: int, config: ServiceConfig):
    """Start the training service.

    Parameters
    ----------
    port : int
        Port to listen on
    config : ServiceConfig
        Service configuration
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    training_service_pb2_grpc.add_TrainingServiceServicer_to_server(
        TrainingService(config=config), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()
