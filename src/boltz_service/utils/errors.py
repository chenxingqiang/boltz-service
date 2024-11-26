"""Error handling utilities for Boltz service."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

import grpc

class ErrorCode(Enum):
    """Error codes for Boltz service."""
    
    # General errors
    UNKNOWN = "UNKNOWN"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    FAILED_PRECONDITION = "FAILED_PRECONDITION"
    ABORTED = "ABORTED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    UNAVAILABLE = "UNAVAILABLE"
    
    # Domain-specific errors
    INVALID_SEQUENCE = "INVALID_SEQUENCE"
    SEQUENCE_TOO_LONG = "SEQUENCE_TOO_LONG"
    MODEL_NOT_FOUND = "MODEL_NOT_FOUND"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    DATABASE_ERROR = "DATABASE_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    
    @classmethod
    def to_grpc_code(cls, code: 'ErrorCode') -> grpc.StatusCode:
        """Convert error code to gRPC status code."""
        mapping = {
            cls.UNKNOWN: grpc.StatusCode.UNKNOWN,
            cls.INVALID_ARGUMENT: grpc.StatusCode.INVALID_ARGUMENT,
            cls.NOT_FOUND: grpc.StatusCode.NOT_FOUND,
            cls.ALREADY_EXISTS: grpc.StatusCode.ALREADY_EXISTS,
            cls.PERMISSION_DENIED: grpc.StatusCode.PERMISSION_DENIED,
            cls.RESOURCE_EXHAUSTED: grpc.StatusCode.RESOURCE_EXHAUSTED,
            cls.FAILED_PRECONDITION: grpc.StatusCode.FAILED_PRECONDITION,
            cls.ABORTED: grpc.StatusCode.ABORTED,
            cls.DEADLINE_EXCEEDED: grpc.StatusCode.DEADLINE_EXCEEDED,
            cls.UNAVAILABLE: grpc.StatusCode.UNAVAILABLE,
            # Map domain-specific errors to appropriate gRPC codes
            cls.INVALID_SEQUENCE: grpc.StatusCode.INVALID_ARGUMENT,
            cls.SEQUENCE_TOO_LONG: grpc.StatusCode.INVALID_ARGUMENT,
            cls.MODEL_NOT_FOUND: grpc.StatusCode.NOT_FOUND,
            cls.INFERENCE_FAILED: grpc.StatusCode.INTERNAL,
            cls.DATABASE_ERROR: grpc.StatusCode.INTERNAL,
            cls.CACHE_ERROR: grpc.StatusCode.INTERNAL,
        }
        return mapping.get(code, grpc.StatusCode.UNKNOWN)

@dataclass
class ServiceError(Exception):
    """Base exception class for Boltz service errors."""
    
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.code.value}: {self.message} - {self.details}"
        return f"{self.code.value}: {self.message}"
    
    def to_grpc_error(self) -> grpc.RpcError:
        """Convert to gRPC error."""
        context = grpc.ServicerContext()
        context.set_code(ErrorCode.to_grpc_code(self.code))
        context.set_details(self.message)
        if self.details:
            context.set_trailing_metadata([
                ('error-details', str(self.details))
            ])
        return context.abort(context.code(), self.message)

class ValidationError(ServiceError):
    """Validation error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.INVALID_ARGUMENT, message, details)

class ResourceNotFoundError(ServiceError):
    """Resource not found error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.NOT_FOUND, message, details)

class ResourceExhaustedError(ServiceError):
    """Resource exhausted error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.RESOURCE_EXHAUSTED, message, details)

class DatabaseError(ServiceError):
    """Database error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.DATABASE_ERROR, message, details)

class CacheError(ServiceError):
    """Cache error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(ErrorCode.CACHE_ERROR, message, details)

def handle_service_error(func):
    """Decorator to handle service errors and convert them to gRPC errors."""
    
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ServiceError as e:
            raise e.to_grpc_error()
        except Exception as e:
            error = ServiceError(ErrorCode.UNKNOWN, str(e))
            raise error.to_grpc_error()
            
    return wrapper
