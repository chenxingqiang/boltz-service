"""
Boltz gRPC server implementation
"""
import os
import grpc
from concurrent import futures
import logging
from pathlib import Path
from typing import Optional

from grpc_health.v1 import health_pb2_grpc, health
from grpc_reflection.v1alpha import reflection

from boltz_service.services.msa import MSAService
from boltz_service.services.inference import InferenceService
from boltz_service.services.training import TrainingService
from boltz_service.data.types import ServiceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BoltzServer:
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 50051,
        max_workers: int = 10,
        config: Optional[ServiceConfig] = None
    ):
        """Initialize Boltz gRPC server

        Parameters
        ----------
        host : str, optional
            Host to bind to, by default "0.0.0.0"
        port : int, optional
            Port to listen on, by default 50051
        max_workers : int, optional
            Number of worker threads, by default 10
        config : Optional[ServiceConfig], optional
            Service configuration, by default None
        """
        self.host = host
        self.port = port
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
        
        # Initialize services
        self.msa_service = MSAService(config)
        self.inference_service = InferenceService(config)
        self.training_service = TrainingService(config)
        
        # Add services to server
        from boltz_service.protos import inference_service_pb2_grpc, inference_service_pb2
        from boltz_service.protos import msa_service_pb2_grpc, msa_service_pb2
        from boltz_service.protos import training_service_pb2_grpc, training_service_pb2
        
        inference_service_pb2_grpc.add_InferenceServiceServicer_to_server(
            self.inference_service, self.server
        )
        msa_service_pb2_grpc.add_MSAServiceServicer_to_server(
            self.msa_service, self.server
        )
        training_service_pb2_grpc.add_TrainingServiceServicer_to_server(
            self.training_service, self.server
        )

        # Add health checking service
        health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self.server)

        # Register services for reflection
        service_names = (
            inference_service_pb2.DESCRIPTOR.services_by_name['InferenceService'].full_name,
            msa_service_pb2.DESCRIPTOR.services_by_name['MSAService'].full_name,
            training_service_pb2.DESCRIPTOR.services_by_name['TrainingService'].full_name,
            reflection.SERVICE_NAME,
            health.SERVICE_NAME,
        )
        reflection.enable_server_reflection(service_names, self.server)

        # Set initial health status
        health_servicer.set('', health_pb2_grpc.HealthCheckResponse.SERVING)
        for service in service_names:
            health_servicer.set(service, health_pb2_grpc.HealthCheckResponse.SERVING)

    def start(self):
        """Start the gRPC server"""
        server_address = f"{self.host}:{self.port}"
        self.server.add_insecure_port(server_address)
        self.server.start()
        logger.info(f"Server started on {server_address}")
        
        try:
            self.server.wait_for_termination()
        except KeyboardInterrupt:
            logger.info("Shutting down server...")
            self.stop()
            
    def stop(self):
        """Stop the gRPC server"""
        self.server.stop(0)
        logger.info("Server stopped")


def serve_grpc(
    host: str = "0.0.0.0",
    port: int = 50051,
    num_workers: int = 10,
    cache_dir: Optional[Path] = None,
    data_path: Optional[Path] = None,
    checkpoint_path: Optional[Path] = None,
    model_path: Optional[Path] = None,
    devices: int = 1,
    accelerator: str = "gpu",
) -> None:
    """Start the Boltz gRPC server.

    Parameters
    ----------
    host : str, optional
        Host to bind to, by default "0.0.0.0"
    port : int, optional
        Port to listen on, by default 50051
    num_workers : int, optional
        Number of worker processes, by default 10
    cache_dir : Optional[Path], optional
        Cache directory, by default None
    data_path : Optional[Path], optional
        Data directory for training, by default None
    checkpoint_path : Optional[Path], optional
        Path for saving model checkpoints, by default None
    model_path : Optional[Path], optional
        Path for saving exported models, by default None
    devices : int, optional
        Number of devices to use, by default 1
    accelerator : str, optional
        Accelerator type (gpu or cpu), by default "gpu"
    """
    # Create service configuration
    config = ServiceConfig(
        cache_dir=cache_dir,
        data_path=data_path,
        checkpoint_path=checkpoint_path,
        model_path=model_path,
        devices=devices,
        accelerator=accelerator,
        num_workers=num_workers,
    )

    # Create and start server
    server = BoltzServer(
        host=host,
        port=port,
        max_workers=num_workers,
        config=config,
    )

    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()

if __name__ == "__main__":
    serve_grpc()
