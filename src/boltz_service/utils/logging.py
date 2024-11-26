"""Logging utilities for Boltz service."""

import json
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from boltz_service.config.base import LogConfig

class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the record as JSON."""
        data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if record.exc_info:
            data['exception'] = self.formatException(record.exc_info)
            
        if hasattr(record, 'request_id'):
            data['request_id'] = record.request_id
            
        return json.dumps(data)

class RequestIdFilter(logging.Filter):
    """Filter that adds request ID to log records."""
    
    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id
        
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request ID to the record."""
        record.request_id = self.request_id
        return True

def setup_logging(config: LogConfig, service_name: str = "boltz") -> logging.Logger:
    """Set up logging with the given configuration.
    
    Parameters
    ----------
    config : LogConfig
        Logging configuration
    service_name : str
        Name of the service for the logger
        
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(config.level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatters
    if config.enable_json_logging:
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(config.format)
        
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if configured)
    if config.file_path:
        log_dir = Path(config.file_path).parent
        os.makedirs(log_dir, exist_ok=True)
        
        if config.rotate_logs:
            file_handler = logging.handlers.RotatingFileHandler(
                config.file_path,
                maxBytes=config.max_bytes,
                backupCount=config.backup_count
            )
        else:
            file_handler = logging.FileHandler(config.file_path)
            
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger

def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name.
    
    Parameters
    ----------
    name : str
        Name for the logger
        
    Returns
    -------
    logging.Logger
        Logger instance
    """
    return logging.getLogger(f"boltz.{name}")

class ServiceLogger:
    """Context manager for service logging."""
    
    def __init__(self, logger: logging.Logger, service_name: str, request_id: Optional[str] = None):
        self.logger = logger
        self.service_name = service_name
        self.request_id = request_id
        self.filter = RequestIdFilter(request_id)
        
    def __enter__(self):
        """Add request ID filter."""
        self.logger.addFilter(self.filter)
        self.logger.info(f"Starting {self.service_name} service", extra={'request_id': self.request_id})
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Remove request ID filter and log any exceptions."""
        if exc_type:
            self.logger.error(
                f"Error in {self.service_name} service",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={'request_id': self.request_id}
            )
        else:
            self.logger.info(f"Completed {self.service_name} service", extra={'request_id': self.request_id})
            
        self.logger.removeFilter(self.filter)
