"""Boltz gRPC server implementation.

This module provides a simplified server interface that wraps the main BoltzServer.
For the full implementation, see boltz_service.main.
"""

import logging
from pathlib import Path
from typing import Optional

from boltz_service.data.types import ServiceConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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

    This is a convenience function that creates a ServiceConfig and starts
    the BoltzServer with the specified parameters.

    Parameters
    ----------
    host : str, optional
        Host to bind to, by default "0.0.0.0"
    port : int, optional
        Port to listen on, by default 50051
    num_workers : int, optional
        Number of worker threads, by default 10
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
    # Import here to avoid circular imports
    from boltz_service.main import BoltzServer
    from boltz_service.config.base import BaseConfig

    # Create base configuration
    config = BaseConfig()
    config.network.host = host
    config.network.port = port
    config.network.max_workers = num_workers
    config.accelerator.type = accelerator
    config.accelerator.device_ids = list(range(devices))

    if cache_dir:
        config.cache.cache_dir = cache_dir

    # Validate configuration
    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Configuration error: {error}")
        raise ValueError("Configuration validation failed")

    # Create and start server
    server = BoltzServer(config)

    try:
        server.start()
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
        server.stop()


# Backwards compatibility alias
class BoltzServer:
    """Backwards compatibility wrapper for BoltzServer.

    This class provides backwards compatibility for code that imports
    BoltzServer from this module. For new code, use boltz_service.main.BoltzServer.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 50051,
        max_workers: int = 10,
        config: Optional[ServiceConfig] = None,
    ):
        """Initialize Boltz gRPC server.

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
        from boltz_service.config.base import BaseConfig
        from boltz_service.main import BoltzServer as MainBoltzServer

        # Create base configuration
        base_config = BaseConfig()
        base_config.network.host = host
        base_config.network.port = port
        base_config.network.max_workers = max_workers

        if config:
            if config.cache_dir:
                base_config.cache.cache_dir = config.cache_dir
            base_config.accelerator.type = config.accelerator
            base_config.accelerator.device_ids = list(range(config.devices))

        self._server = MainBoltzServer(base_config)
        self.host = host
        self.port = port

    def start(self):
        """Start the gRPC server."""
        self._server.start()
        self._server.wait_for_termination()

    def stop(self):
        """Stop the gRPC server."""
        self._server.stop()


if __name__ == "__main__":
    serve_grpc()
