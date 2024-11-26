"""Main entry point for Boltz service."""

import argparse
import asyncio
import os
import signal
import sys
from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc
from grpc_health.v1 import health, health_pb2, health_pb2_grpc
from grpc_reflection.v1alpha import reflection

from boltz_service.config.base import BaseConfig
from boltz_service.protos import (
    inference_service_pb2_grpc,
    msa_service_pb2_grpc,
    training_service_pb2_grpc,
)
from boltz_service.services.inference import InferenceService
from boltz_service.services.msa import MSAService
from boltz_service.services.training import TrainingService
from boltz_service.utils.errors import ServiceError
from boltz_service.utils.logging import setup_logging, get_logger
from boltz_service.utils.resources import ResourceManager

# Initialize logger
logger = get_logger(__name__)

class BoltzServer:
    """Main server class for Boltz service."""
    
    def __init__(self, config: BaseConfig):
        """Initialize server.
        
        Parameters
        ----------
        config : BaseConfig
            Server configuration
        """
        self.config = config
        self.logger = setup_logging(config.logging, "boltz")
        self.resource_manager = ResourceManager(config.accelerator)
        
        # Initialize server
        self.server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=config.network.max_workers),
            maximum_concurrent_rpcs=config.network.max_concurrent_rpcs,
            options=[
                ('grpc.keepalive_time_ms', config.network.keepalive_time_ms),
                ('grpc.keepalive_timeout_ms', 20000),
                ('grpc.keepalive_permit_without_calls', True),
                ('grpc.http2.max_pings_without_data', 0),
                ('grpc.http2.min_time_between_pings_ms', 10000),
                ('grpc.http2.min_ping_interval_without_data_ms', 5000),
            ]
        )
        
        # Add services
        self._add_services()
        
        # Add health checking
        health_servicer = health.HealthServicer(
            experimental_non_blocking=True,
            experimental_thread_pool=futures.ThreadPoolExecutor(max_workers=4)
        )
        health_pb2_grpc.add_HealthServicer_to_server(health_servicer, self.server)
        
        # Enable reflection
        service_names = (
            reflection.SERVICE_NAME,
            health.SERVICE_NAME,
            *self.server.get_service_names()
        )
        reflection.enable_server_reflection(service_names, self.server)
        
    def _add_services(self):
        """Add all services to the server."""
        try:
            # Inference service
            inference_service = InferenceService(self.config)
            inference_service_pb2_grpc.add_InferenceServiceServicer_to_server(
                inference_service, self.server
            )
            
            # MSA service
            msa_service = MSAService(self.config)
            msa_service_pb2_grpc.add_MSAServiceServicer_to_server(
                msa_service, self.server
            )
            
            # Training service
            training_service = TrainingService(self.config)
            training_service_pb2_grpc.add_TrainingServiceServicer_to_server(
                training_service, self.server
            )
            
        except Exception as e:
            raise ServiceError("Failed to initialize services", str(e))
            
    def start(self):
        """Start the server."""
        # Add secure credentials if SSL is enabled
        if self.config.security.enable_ssl:
            with open(self.config.security.cert_path, 'rb') as f:
                cert = f.read()
            with open(self.config.security.key_path, 'rb') as f:
                key = f.read()
                
            credentials = grpc.ssl_server_credentials(
                [(key, cert)],
                require_client_auth=self.config.security.require_client_auth
            )
            self.server.add_secure_port(
                f"{self.config.network.host}:{self.config.network.port}",
                credentials
            )
        else:
            self.server.add_insecure_port(
                f"{self.config.network.host}:{self.config.network.port}"
            )
            
        # Start server
        self.server.start()
        logger.info(
            f"Server started on {self.config.network.host}:{self.config.network.port}"
        )
        
        # Set up signal handlers
        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, self._handle_shutdown)
            
        # Start resource monitoring
        self.resource_manager.monitor.start()
        
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal")
        self.stop()
        sys.exit(0)
        
    def stop(self):
        """Stop the server."""
        logger.info("Stopping server...")
        
        # Stop accepting new requests
        self.server.stop(grace=5)
        
        # Clean up resources
        self.resource_manager.cleanup()
        
        logger.info("Server stopped")
        
    def wait_for_termination(self):
        """Wait for server termination."""
        self.server.wait_for_termination()

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Boltz Service")
    
    # Server commands
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    serve_parser.add_argument("--port", type=int, default=50051, help="Port to bind to")
    serve_parser.add_argument(
        "--workers", type=int, default=10, help="Number of worker threads"
    )
    serve_parser.add_argument(
        "--cache", default="~/.boltz", help="Cache directory"
    )
    serve_parser.add_argument(
        "--devices", type=int, default=1, help="Number of devices to use"
    )
    serve_parser.add_argument(
        "--accelerator",
        choices=["cpu", "gpu"],
        default="cpu",
        help="Accelerator type"
    )
    
    return parser.parse_args()

def main():
    """Main entry point."""
    print("Starting Boltz service...")
    try:
        args = parse_args()
        
        if args.command == "serve":
            # Create configuration
            config = BaseConfig()
            
            # Update from command line args
            config.network.host = args.host
            config.network.port = args.port
            config.network.max_workers = args.workers
            config.cache.cache_dir = Path(os.path.expanduser(args.cache))
            config.accelerator.type = args.accelerator
            config.accelerator.device_ids = list(range(args.devices))
            
            # Validate configuration
            errors = config.validate()
            if errors:
                logger.error("Configuration validation failed:")
                for error in errors:
                    logger.error(f"- {error}")
                sys.exit(1)
                
            # Start server
            server = BoltzServer(config)
            try:
                server.start()
                server.wait_for_termination()
            except Exception as e:
                logger.error(f"Server failed: {e}")
                sys.exit(1)
                
    except Exception as e:
        print(f"Error starting service: {str(e)}")
        raise

if __name__ == "__main__":
    main()
