"""Prometheus integration for Boltz service."""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from prometheus_client import REGISTRY, CollectorRegistry, Gauge, generate_latest
from prometheus_client.multiprocess import MultiProcessCollector

from boltz_service.config.base import MetricsConfig
from boltz_service.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar('T')

class PrometheusManager:
    """Manager for Prometheus metrics integration."""
    
    def __init__(self, config: MetricsConfig):
        """Initialize Prometheus manager.
        
        Parameters
        ----------
        config : MetricsConfig
            Metrics configuration
        """
        self.config = config
        self.registry = REGISTRY
        
        # System metrics
        self.process_start_time = Gauge(
            'boltz_process_start_time_seconds',
            'Start time of the process since unix epoch in seconds',
            registry=self.registry
        )
        self.process_start_time.set_to_current_time()
        
        # Resource metrics
        self.process_resident_memory = Gauge(
            'boltz_process_resident_memory_bytes',
            'Resident memory size in bytes',
            registry=self.registry
        )
        
        self.process_virtual_memory = Gauge(
            'boltz_process_virtual_memory_bytes',
            'Virtual memory size in bytes',
            registry=self.registry
        )
        
        self.process_cpu_seconds = Gauge(
            'boltz_process_cpu_seconds_total',
            'Total user and system CPU time spent in seconds',
            registry=self.registry
        )
        
        # Initialize multiprocess mode if needed
        if config.enable_multiprocess:
            self.registry = CollectorRegistry()
            MultiProcessCollector(self.registry)
            
    def instrument(self, name: str, description: str, labels: Optional[Dict[str, str]] = None) -> Callable:
        """Decorator to instrument a function with Prometheus metrics.
        
        Parameters
        ----------
        name : str
            Metric name
        description : str
            Metric description
        labels : Optional[Dict[str, str]]
            Additional labels for the metric
            
        Returns
        -------
        Callable
            Decorated function
        """
        if labels is None:
            labels = {}
            
        duration_metric = Gauge(
            f'boltz_{name}_duration_seconds',
            f'Duration of {description} in seconds',
            list(labels.keys()),
            registry=self.registry
        )
        
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration = time.time() - start_time
                    duration_metric.labels(**labels).set(duration)
            return wrapper
        return decorator
    
    def get_metrics(self) -> bytes:
        """Get current metrics in Prometheus format.
        
        Returns
        -------
        bytes
            Metrics in Prometheus format
        """
        return generate_latest(self.registry)
    
    def update_resource_metrics(self, process: Any):
        """Update process resource metrics.
        
        Parameters
        ----------
        process : Any
            Process object with memory_info() and cpu_times() methods
        """
        try:
            memory_info = process.memory_info()
            self.process_resident_memory.set(memory_info.rss)
            self.process_virtual_memory.set(memory_info.vms)
            
            cpu_times = process.cpu_times()
            self.process_cpu_seconds.set(cpu_times.user + cpu_times.system)
        except Exception as e:
            logger.warning(f"Failed to update resource metrics: {e}")
            
    def clear(self):
        """Clear all metrics."""
        for collector in list(self.registry._collector_to_names.keys()):
            self.registry.unregister(collector)
