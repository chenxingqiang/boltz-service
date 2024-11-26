"""Base configuration management for Boltz service."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class AcceleratorConfig:
    """Configuration for compute accelerators."""
    type: str = "cpu"  # cpu, gpu, tpu
    device_ids: List[int] = field(default_factory=lambda: [0])
    memory_limit: Optional[int] = None  # in MB

@dataclass
class NetworkConfig:
    """Network-related configuration."""
    host: str = "0.0.0.0"
    port: int = 50051
    max_workers: int = 10
    max_concurrent_rpcs: int = 100
    keepalive_time_ms: int = 7200000  # 2 hours

@dataclass
class SecurityConfig:
    """Security-related configuration."""
    enable_ssl: bool = False
    cert_path: Optional[str] = None
    key_path: Optional[str] = None
    require_client_auth: bool = False
    allowed_clients: List[str] = field(default_factory=list)

@dataclass
class CacheConfig:
    """Cache configuration."""
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".boltz" / "cache")
    max_cache_size_gb: int = 100
    enable_redis: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

@dataclass
class DatabaseConfig:
    """Database configuration."""
    db_type: str = "sqlite"  # sqlite, postgres
    db_path: Optional[str] = None
    host: str = "localhost"
    port: int = 5432
    name: str = "boltz"
    user: str = "boltz"
    password: str = ""
    pool_size: int = 5
    max_overflow: int = 10

@dataclass
class LogConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    rotate_logs: bool = True
    max_bytes: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    enable_json_logging: bool = False

@dataclass
class MetricsConfig:
    """Metrics and monitoring configuration."""
    enable_prometheus: bool = False
    prometheus_port: int = 9090
    prometheus_host: str = "localhost"
    enable_tracing: bool = False
    jaeger_host: str = "localhost"
    jaeger_port: int = 6831
    jaeger_query_port: int = 16686
    enable_multiprocess: bool = False
    collection_interval: float = 15.0  # seconds
    retention_days: int = 7
    max_traces_per_second: int = 100
    max_attributes_per_span: int = 32
    max_events_per_span: int = 128
    max_links_per_span: int = 32
    export_timeout_ms: int = 30000
    max_export_batch_size: int = 512
    scheduled_delay_ms: int = 5000
    max_queue_size: int = 2048
    
    # Grafana settings
    grafana_host: str = "localhost"
    grafana_port: int = 3000
    grafana_api_key: str = ""
    grafana_notification_channel: str = "general"
    
    # Loki settings
    loki_host: str = "localhost"
    loki_port: int = 3100

@dataclass
class BaseConfig:
    """Base configuration for Boltz service."""
    
    # Service identification
    service_name: str = "boltz"
    service_version: str = "0.1.0"
    environment: str = "development"
    
    # Component configurations
    network: NetworkConfig = field(default_factory=NetworkConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    accelerator: AcceleratorConfig = field(default_factory=AcceleratorConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LogConfig = field(default_factory=LogConfig)
    metrics: MetricsConfig = field(default_factory=MetricsConfig)
    
    # Service-specific settings
    max_sequence_length: int = 2000
    max_batch_size: int = 32
    timeout_seconds: int = 3600
    retry_attempts: int = 3
    
    @classmethod
    def from_env(cls) -> 'BaseConfig':
        """Create configuration from environment variables."""
        config = cls()
        
        # Load environment variables with BOLTZ_ prefix
        for key, value in os.environ.items():
            if key.startswith("BOLTZ_"):
                config._set_from_env(key[6:].lower(), value)
                
        return config
    
    def _set_from_env(self, key: str, value: str):
        """Set configuration value from environment variable."""
        parts = key.split('_')
        current = self
        
        # Navigate through nested attributes
        for part in parts[:-1]:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return
                
        # Set the final attribute if it exists
        final_attr = parts[-1]
        if hasattr(current, final_attr):
            attr_type = type(getattr(current, final_attr))
            try:
                if attr_type == bool:
                    setattr(current, final_attr, value.lower() in ('true', '1', 'yes'))
                elif attr_type == int:
                    setattr(current, final_attr, int(value))
                elif attr_type == float:
                    setattr(current, final_attr, float(value))
                elif attr_type == list:
                    setattr(current, final_attr, value.split(','))
                else:
                    setattr(current, final_attr, value)
            except (ValueError, TypeError):
                pass  # Skip invalid values
                
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors."""
        errors = []
        
        # Validate cache directory
        if not self.cache.cache_dir.parent.exists():
            errors.append(f"Parent directory for cache does not exist: {self.cache.cache_dir.parent}")
            
        # Validate port ranges
        if not 0 <= self.network.port <= 65535:
            errors.append(f"Invalid port number: {self.network.port}")
            
        # Validate SSL configuration
        if self.security.enable_ssl:
            if not self.security.cert_path or not self.security.key_path:
                errors.append("SSL enabled but cert_path or key_path not provided")
            elif not os.path.exists(self.security.cert_path):
                errors.append(f"SSL cert file not found: {self.security.cert_path}")
            elif not os.path.exists(self.security.key_path):
                errors.append(f"SSL key file not found: {self.security.key_path}")
                
        return errors
