"""Server configuration for Boltz service."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from boltz_service.config.base import BaseConfig

@dataclass
class ServerConfig(BaseConfig):
    """Server-specific configuration."""
    
    # Model configuration
    model_name: str = "boltz-1"
    model_version: str = "v1.0.0"
    model_cache: Path = field(default_factory=lambda: Path.home() / ".boltz" / "models")
    model_config: Dict = field(default_factory=dict)
    
    # Inference configuration
    max_sequence_length: int = 2000
    max_batch_size: int = 32
    recycling_steps: int = 3
    sampling_steps: int = 200
    diffusion_samples: int = 1
    
    # MSA configuration
    max_msa_sequences: int = 4096
    min_sequence_identity: float = 0.3
    max_sequence_identity: float = 0.9
    
    # Training configuration
    learning_rate: float = 1e-4
    weight_decay: float = 0.01
    warmup_steps: int = 1000
    max_epochs: int = 100
    gradient_clip_val: float = 1.0
    
    def validate(self) -> List[str]:
        """Validate server configuration.
        
        Returns
        -------
        List[str]
            List of validation errors
        """
        errors = super().validate()
        
        # Validate model configuration
        if not self.model_cache.exists():
            self.model_cache.mkdir(parents=True, exist_ok=True)
            
        # Validate sequence parameters
        if self.max_sequence_length <= 0:
            errors.append("max_sequence_length must be positive")
            
        if self.max_batch_size <= 0:
            errors.append("max_batch_size must be positive")
            
        if self.recycling_steps <= 0:
            errors.append("recycling_steps must be positive")
            
        if self.sampling_steps <= 0:
            errors.append("sampling_steps must be positive")
            
        if self.diffusion_samples <= 0:
            errors.append("diffusion_samples must be positive")
            
        # Validate MSA parameters
        if self.max_msa_sequences <= 0:
            errors.append("max_msa_sequences must be positive")
            
        if not 0 <= self.min_sequence_identity <= 1:
            errors.append("min_sequence_identity must be between 0 and 1")
            
        if not 0 <= self.max_sequence_identity <= 1:
            errors.append("max_sequence_identity must be between 0 and 1")
            
        if self.min_sequence_identity >= self.max_sequence_identity:
            errors.append("min_sequence_identity must be less than max_sequence_identity")
            
        # Validate training parameters
        if self.learning_rate <= 0:
            errors.append("learning_rate must be positive")
            
        if self.weight_decay < 0:
            errors.append("weight_decay must be non-negative")
            
        if self.warmup_steps < 0:
            errors.append("warmup_steps must be non-negative")
            
        if self.max_epochs <= 0:
            errors.append("max_epochs must be positive")
            
        if self.gradient_clip_val <= 0:
            errors.append("gradient_clip_val must be positive")
            
        return errors
    
    @classmethod
    def from_env(cls) -> 'ServerConfig':
        """Create server configuration from environment variables.
        
        Returns
        -------
        ServerConfig
            Server configuration
        """
        config = super().from_env()
        
        # Add model-specific configuration
        if "BOLTZ_MODEL_CONFIG" in os.environ:
            config.model_config = json.loads(os.environ["BOLTZ_MODEL_CONFIG"])
            
        return config
