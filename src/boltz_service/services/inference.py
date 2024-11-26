"""
Boltz inference service implementation
"""
import logging
import os
from concurrent import futures
from typing import Dict, List, Optional
from pathlib import Path

import grpc
import torch
from mashumaro import DataClassDictMixin
from dataclasses import dataclass

from boltz_service.data.module.inference import BoltzInferenceDataModule
from boltz_service.data.parse.fasta import parse_fasta
from boltz_service.model.model import BoltzModel
from boltz_service.data.types import Chain, EntityType, ServiceConfig
from boltz_service.data.write.writer import save_prediction

# Generated proto code
from boltz_service.protos import inference_service_pb2, inference_service_pb2_grpc, common_pb2

logger = logging.getLogger(__name__)

@dataclass
class PredictionJob(DataClassDictMixin):
    """Prediction job"""
    job_id: str
    sequence: str
    recycling_steps: int = 3
    sampling_steps: int = 200
    diffusion_samples: int = 1
    output_format: str = "mmcif"
    model_version: str = "latest"
    status: str = "pending"
    result_path: Optional[str] = None
    error_message: Optional[str] = None

class InferenceService(inference_service_pb2_grpc.InferenceServiceServicer):
    """Inference service implementation"""
    
    def __init__(
        self,
        config: ServiceConfig,
    ):
        """Initialize inference service

        Parameters
        ----------
        config : ServiceConfig
            Service configuration
        """
        self.config = config
        self.cache_dir = config.cache_dir
        self.model_path = os.path.join(self.cache_dir, "models")
        
        # Load models
        self._load_models()
        
        # Job queue
        self.jobs: Dict[str, PredictionJob] = {}
        
    def _load_models(self):
        """Load models"""
        # Load all available model versions
        self.models = {}
        for model_dir in os.listdir(self.model_path):
            if os.path.isdir(os.path.join(self.model_path, model_dir)):
                try:
                    model = BoltzModel.load_from_checkpoint(
                        os.path.join(self.model_path, model_dir, "model.ckpt")
                    )
                    model.eval()
                    if torch.cuda.is_available():
                        model = model.cuda()
                    self.models[model_dir] = model
                except Exception as e:
                    logger.error(f"Failed to load model {model_dir}: {e}")
        
        if not self.models:
            raise RuntimeError("No models available")
            
        # Set latest version
        latest_version = max(self.models.keys())
        self.models["latest"] = self.models[latest_version]
        
    def PredictStructure(
        self,
        request: inference_service_pb2.PredictionRequest,
        context: grpc.ServicerContext
    ) -> inference_service_pb2.PredictionResponse:
        """Handle single prediction request"""
        try:
            # Create prediction job
            job = PredictionJob(
                job_id=request.job_id,
                sequence=request.sequence,
                recycling_steps=request.recycling_steps,
                sampling_steps=request.sampling_steps,
                diffusion_samples=request.diffusion_samples,
                output_format=request.output_format,
                model_version=request.model_version,
            )
            
            # Save job
            self.jobs[job.job_id] = job
            
            # Run prediction
            result_path = self._run_prediction(job)
            
            # Update job status
            job.status = "completed"
            job.result_path = result_path
            
            return inference_service_pb2.PredictionResponse(
                job_id=job.job_id,
                status=job.status,
                result_path=job.result_path,
                error_message=job.error_message,
            )
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return inference_service_pb2.PredictionResponse(
                job_id=request.job_id,
                status="failed",
                error_message=str(e),
            )
            
    def GetJobStatus(
        self,
        request: common_pb2.JobStatusRequest,
        context: grpc.ServicerContext
    ) -> common_pb2.JobStatusResponse:
        """Get job status"""
        try:
            job = self.jobs.get(request.job_id)
            if not job:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Job {request.job_id} not found")
                return common_pb2.JobStatusResponse()
                
            return common_pb2.JobStatusResponse(
                job_id=job.job_id,
                status=job.status,
                progress=1.0 if job.status == "completed" else 0.0,
                result_path=job.result_path,
                error_message=job.error_message,
            )
            
        except Exception as e:
            logger.error(f"Failed to get job status: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.JobStatusResponse()
            
    def CancelJob(
        self,
        request: common_pb2.CancelJobRequest,
        context: grpc.ServicerContext
    ) -> common_pb2.CancelJobResponse:
        """Cancel job"""
        try:
            job = self.jobs.get(request.job_id)
            if not job:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Job {request.job_id} not found")
                return common_pb2.CancelJobResponse()
                
            # Update job status
            job.status = "cancelled"
            
            return common_pb2.CancelJobResponse(
                job_id=job.job_id,
                status=job.status,
            )
            
        except Exception as e:
            logger.error(f"Failed to cancel job: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return common_pb2.CancelJobResponse()
            
    def _run_prediction(self, job: PredictionJob) -> str:
        """Run prediction

        Parameters
        ----------
        job : PredictionJob
            Prediction job

        Returns
        -------
        str
            Path to prediction result
        """
        # Create output directory
        output_dir = os.path.join(self.cache_dir, "predictions", job.job_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Get model
        model = self.models[job.model_version]
        
        # Create data module
        data_module = BoltzInferenceDataModule(
            sequences=[job.sequence],
            batch_size=1,
            num_workers=2,
        )
        
        # Run prediction
        predictions = model.predict(
            datamodule=data_module,
            recycling_steps=job.recycling_steps,
            sampling_steps=job.sampling_steps,
            diffusion_samples=job.diffusion_samples,
        )
        
        # Save prediction
        output_path = os.path.join(output_dir, f"prediction.{job.output_format}")
        save_prediction(predictions[0], output_path, format=job.output_format)
        
        return output_path

def serve(
    port: int,
    config: ServiceConfig,
):
    """Start service"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    inference_service_pb2_grpc.add_InferenceServiceServicer_to_server(
        InferenceService(
            config=config,
        ),
        server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()
