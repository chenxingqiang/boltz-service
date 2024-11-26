"""Monitoring service for Boltz."""

import os
import time
from typing import Optional

import psutil

from boltz_service.config.base import BaseConfig
from boltz_service.utils.logging import get_logger
from boltz_service.utils.metrics import MetricsManager
from boltz_service.utils.prometheus import PrometheusManager
from boltz_service.utils.tracing import TracingManager

logger = get_logger(__name__)

class MonitoringService:
    """Service for managing monitoring, metrics, and tracing."""
    
    def __init__(self, config: BaseConfig):
        """Initialize monitoring service.
        
        Parameters
        ----------
        config : BaseConfig
            Service configuration
        """
        self.config = config
        self.process = psutil.Process(os.getpid())
        
        # Initialize managers
        self.metrics_manager = MetricsManager(config.metrics)
        self.prometheus_manager = PrometheusManager(config.metrics)
        self.tracing_manager = TracingManager(
            config.metrics,
            config.service_name
        )
        
        # Start background monitoring if enabled
        if config.metrics.enable_prometheus:
            self._start_monitoring()
            
    def _start_monitoring(self):
        """Start background resource monitoring."""
        try:
            while True:
                self._update_metrics()
                time.sleep(self.config.metrics.collection_interval)
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}")
            
    def _update_metrics(self):
        """Update all metrics."""
        try:
            # Update process metrics
            self.prometheus_manager.update_resource_metrics(self.process)
            
            # Update custom metrics
            self._update_custom_metrics()
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
            
    def _update_custom_metrics(self):
        """Update custom service metrics."""
        try:
            # Get CPU stats
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics_manager.update_resource_metrics(
                cpu_util=cpu_percent,
                memory_util=psutil.virtual_memory().percent
            )
            
            # Get GPU stats if available
            try:
                import pynvml
                pynvml.nvmlInit()
                device_count = pynvml.nvmlDeviceGetCount()
                
                gpu_utils = []
                gpu_memory_utils = []
                
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    
                    # GPU utilization
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_utils.append(util.gpu)
                    
                    # GPU memory
                    memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    memory_util = (memory.used / memory.total) * 100
                    gpu_memory_utils.append(memory_util)
                    
                self.metrics_manager.update_resource_metrics(
                    cpu_util=cpu_percent,
                    memory_util=psutil.virtual_memory().percent,
                    gpu_utils=gpu_utils,
                    gpu_memory_utils=gpu_memory_utils
                )
                
                pynvml.nvmlShutdown()
            except ImportError:
                logger.debug("NVIDIA management library not available")
            except Exception as e:
                logger.warning(f"Error getting GPU metrics: {e}")
                
        except Exception as e:
            logger.error(f"Error updating custom metrics: {e}")
            
    def start_request_trace(
        self,
        request_id: str,
        method: str,
        attributes: Optional[dict] = None
    ):
        """Start a new request trace.
        
        Parameters
        ----------
        request_id : str
            Unique request identifier
        method : str
            Request method name
        attributes : Optional[dict]
            Additional span attributes
        """
        if attributes is None:
            attributes = {}
            
        attributes.update({
            "request_id": request_id,
            "method": method
        })
        
        return self.tracing_manager.span(
            f"{method}_request",
            attributes=attributes,
            kind=trace.SpanKind.SERVER
        )
        
    def record_model_metrics(
        self,
        model_name: str,
        model_version: str,
        batch_size: Optional[int] = None,
        sequence_length: Optional[int] = None
    ):
        """Record model-specific metrics.
        
        Parameters
        ----------
        model_name : str
            Model name
        model_version : str
            Model version
        batch_size : Optional[int]
            Batch size
        sequence_length : Optional[int]
            Sequence length
        """
        return self.metrics_manager.record_model_metrics(
            model_name=model_name,
            model_version=model_version,
            batch_size=batch_size,
            sequence_length=sequence_length
        )
        
    def record_cache_access(
        self,
        cache_type: str,
        hit: bool,
        size: Optional[int] = None
    ):
        """Record cache access metrics.
        
        Parameters
        ----------
        cache_type : str
            Type of cache
        hit : bool
            Whether the access was a hit
        size : Optional[int]
            Current cache size in bytes
        """
        self.metrics_manager.record_cache_metrics(
            cache_type=cache_type,
            hit=hit,
            size=size
        )
        
    def instrument(self, name: str, description: str):
        """Decorator to instrument a function with metrics and tracing.
        
        Parameters
        ----------
        name : str
            Metric name
        description : str
            Metric description
        """
        def decorator(func):
            # Combine Prometheus and tracing decorators
            prometheus_decorator = self.prometheus_manager.instrument(
                name,
                description
            )
            trace_decorator = self.tracing_manager.trace(
                name,
                kind=trace.SpanKind.INTERNAL
            )
            
            # Apply both decorators
            return prometheus_decorator(trace_decorator(func))
        return decorator
        
    def shutdown(self):
        """Shutdown monitoring service."""
        try:
            # Clear Prometheus metrics
            self.prometheus_manager.clear()
            
            logger.info("Monitoring service shutdown complete")
        except Exception as e:
            logger.error(f"Error during monitoring service shutdown: {e}")
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
