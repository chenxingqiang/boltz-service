"""Distributed tracing integration using Jaeger."""

import functools
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Generator, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Status, StatusCode

from boltz_service.config.base import MetricsConfig
from boltz_service.utils.logging import get_logger

logger = get_logger(__name__)

# Type variable for function return type
T = TypeVar('T')

class TracingManager:
    """Manager for distributed tracing using Jaeger."""
    
    def __init__(self, config: MetricsConfig, service_name: str):
        """Initialize tracing manager.
        
        Parameters
        ----------
        config : MetricsConfig
            Metrics configuration
        service_name : str
            Name of the service
        """
        self.config = config
        self.service_name = service_name
        
        if config.enable_tracing:
            try:
                # Create Jaeger exporter
                jaeger_exporter = JaegerExporter(
                    agent_host_name=config.jaeger_host,
                    agent_port=config.jaeger_port,
                )
                
                # Create TracerProvider with service name
                provider = TracerProvider(
                    resource=Resource.create({"service.name": service_name})
                )
                
                # Add Jaeger exporter to provider
                provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
                
                # Set global TracerProvider
                trace.set_tracer_provider(provider)
                
                # Get tracer
                self.tracer = trace.get_tracer(__name__)
                logger.info(f"Initialized Jaeger tracing for service {service_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Jaeger tracing: {e}")
                self.tracer = None
        else:
            self.tracer = None
            
    def trace(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> Callable:
        """Decorator to trace a function.
        
        Parameters
        ----------
        name : str
            Name of the span
        attributes : Optional[Dict[str, Any]]
            Additional attributes for the span
        kind : Optional[trace.SpanKind]
            Kind of span
            
        Returns
        -------
        Callable
            Decorated function
        """
        def decorator(func: Callable[..., T]) -> Callable[..., T]:
            @functools.wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> T:
                if not self.tracer:
                    return func(*args, **kwargs)
                    
                with self.tracer.start_as_current_span(
                    name,
                    attributes=attributes,
                    kind=kind
                ) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as e:
                        span.set_status(
                            Status(StatusCode.ERROR, str(e))
                        )
                        span.record_exception(e)
                        raise
            return wrapper
        return decorator
        
    @contextmanager
    def span(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        kind: Optional[trace.SpanKind] = None
    ) -> Generator[Optional[trace.Span], None, None]:
        """Context manager to create a span.
        
        Parameters
        ----------
        name : str
            Name of the span
        attributes : Optional[Dict[str, Any]]
            Additional attributes for the span
        kind : Optional[trace.SpanKind]
            Kind of span
            
        Yields
        ------
        Optional[trace.Span]
            Current span if tracing is enabled, None otherwise
        """
        if not self.tracer:
            yield None
            return
            
        with self.tracer.start_span(
            name,
            attributes=attributes,
            kind=kind
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_status(
                    Status(StatusCode.ERROR, str(e))
                )
                span.record_exception(e)
                raise
                
    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None
    ):
        """Add an event to the current span.
        
        Parameters
        ----------
        name : str
            Name of the event
        attributes : Optional[Dict[str, Any]]
            Additional attributes for the event
        """
        if not self.tracer:
            return
            
        current_span = trace.get_current_span()
        if current_span:
            current_span.add_event(
                name,
                attributes=attributes,
                timestamp=int(time.time_ns())
            )
            
    def set_attribute(self, key: str, value: Any):
        """Set an attribute on the current span.
        
        Parameters
        ----------
        key : str
            Attribute key
        value : Any
            Attribute value
        """
        if not self.tracer:
            return
            
        current_span = trace.get_current_span()
        if current_span:
            current_span.set_attribute(key, value)
            
    def record_exception(self, exception: Exception):
        """Record an exception on the current span.
        
        Parameters
        ----------
        exception : Exception
            Exception to record
        """
        if not self.tracer:
            return
            
        current_span = trace.get_current_span()
        if current_span:
            current_span.record_exception(exception)
            current_span.set_status(
                Status(StatusCode.ERROR, str(exception))
            )
