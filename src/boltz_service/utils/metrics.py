"""Metrics collection utilities for Boltz service."""

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from prometheus_client import Counter, Gauge, Histogram, start_http_server

from boltz_service.config.base import MetricsConfig
from boltz_service.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ServiceMetrics:
    """Service-level metrics."""
    
    # Request metrics
    request_count: Counter = field(
        default_factory=lambda: Counter(
            'boltz_requests_total',
            'Total number of requests',
            ['service', 'method', 'status']
        )
    )
    
    request_duration: Histogram = field(
        default_factory=lambda: Histogram(
            'boltz_request_duration_seconds',
            'Request duration in seconds',
            ['service', 'method'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, float('inf'))
        )
    )
    
    # Resource metrics
    gpu_utilization: Gauge = field(
        default_factory=lambda: Gauge(
            'boltz_gpu_utilization',
            'GPU utilization percentage',
            ['device']
        )
    )
    
    gpu_memory: Gauge = field(
        default_factory=lambda: Gauge(
            'boltz_gpu_memory_bytes',
            'GPU memory usage in bytes',
            ['device']
        )
    )
    
    cpu_utilization: Gauge = field(
        default_factory=lambda: Gauge(
            'boltz_cpu_utilization',
            'CPU utilization percentage'
        )
    )
    
    memory_utilization: Gauge = field(
        default_factory=lambda: Gauge(
            'boltz_memory_utilization',
            'Memory utilization percentage'
        )
    )
    
    # Cache metrics
    cache_hits: Counter = field(
        default_factory=lambda: Counter(
            'boltz_cache_hits_total',
            'Total number of cache hits',
            ['cache_type']
        )
    )
    
    cache_misses: Counter = field(
        default_factory=lambda: Counter(
            'boltz_cache_misses_total',
            'Total number of cache misses',
            ['cache_type']
        )
    )
    
    cache_size: Gauge = field(
        default_factory=lambda: Gauge(
            'boltz_cache_size_bytes',
            'Cache size in bytes',
            ['cache_type']
        )
    )
    
    # Model metrics
    model_load_time: Histogram = field(
        default_factory=lambda: Histogram(
            'boltz_model_load_time_seconds',
            'Model load time in seconds',
            ['model_name', 'model_version']
        )
    )
    
    inference_time: Histogram = field(
        default_factory=lambda: Histogram(
            'boltz_inference_time_seconds',
            'Model inference time in seconds',
            ['model_name', 'model_version']
        )
    )
    
    batch_size: Histogram = field(
        default_factory=lambda: Histogram(
            'boltz_batch_size',
            'Batch size distribution',
            ['model_name']
        )
    )
    
    sequence_length: Histogram = field(
        default_factory=lambda: Histogram(
            'boltz_sequence_length',
            'Sequence length distribution',
            ['model_name']
        )
    )

class MetricsManager:
    """Manage service metrics collection."""
    
    def __init__(self, config: MetricsConfig):
        """Initialize metrics manager.
        
        Parameters
        ----------
        config : MetricsConfig
            Metrics configuration
        """
        self.config = config
        self.metrics = ServiceMetrics()
        
        if config.enable_prometheus:
            try:
                start_http_server(config.prometheus_port)
                logger.info(f"Started Prometheus metrics server on port {config.prometheus_port}")
            except Exception as e:
                logger.error(f"Failed to start Prometheus metrics server: {e}")
                
    @contextmanager
    def record_request(self, service: str, method: str):
        """Record request metrics.
        
        Parameters
        ----------
        service : str
            Service name
        method : str
            Method name
        """
        start_time = time.time()
        try:
            yield
            self.metrics.request_count.labels(service, method, "success").inc()
        except Exception:
            self.metrics.request_count.labels(service, method, "error").inc()
            raise
        finally:
            duration = time.time() - start_time
            self.metrics.request_duration.labels(service, method).observe(duration)
            
    def update_resource_metrics(
        self,
        cpu_util: float,
        memory_util: float,
        gpu_utils: Optional[List[float]] = None,
        gpu_memory_utils: Optional[List[float]] = None
    ):
        """Update resource utilization metrics.
        
        Parameters
        ----------
        cpu_util : float
            CPU utilization percentage
        memory_util : float
            Memory utilization percentage
        gpu_utils : Optional[List[float]]
            GPU utilization percentages
        gpu_memory_utils : Optional[List[float]]
            GPU memory utilization percentages
        """
        self.metrics.cpu_utilization.set(cpu_util)
        self.metrics.memory_utilization.set(memory_util)
        
        if gpu_utils:
            for i, util in enumerate(gpu_utils):
                self.metrics.gpu_utilization.labels(f"gpu{i}").set(util)
                
        if gpu_memory_utils:
            for i, util in enumerate(gpu_memory_utils):
                self.metrics.gpu_memory.labels(f"gpu{i}").set(util)
                
    def record_cache_metrics(
        self,
        cache_type: str,
        hit: bool,
        size: Optional[int] = None
    ):
        """Record cache metrics.
        
        Parameters
        ----------
        cache_type : str
            Type of cache
        hit : bool
            Whether the cache access was a hit
        size : Optional[int]
            Current cache size in bytes
        """
        if hit:
            self.metrics.cache_hits.labels(cache_type).inc()
        else:
            self.metrics.cache_misses.labels(cache_type).inc()
            
        if size is not None:
            self.metrics.cache_size.labels(cache_type).set(size)
            
    @contextmanager
    def record_model_metrics(
        self,
        model_name: str,
        model_version: str,
        batch_size: Optional[int] = None,
        sequence_length: Optional[int] = None
    ):
        """Record model metrics.
        
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
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.metrics.inference_time.labels(model_name, model_version).observe(duration)
            
            if batch_size is not None:
                self.metrics.batch_size.labels(model_name).observe(batch_size)
                
            if sequence_length is not None:
                self.metrics.sequence_length.labels(model_name).observe(sequence_length)
