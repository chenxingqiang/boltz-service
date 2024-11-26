"""Resource management utilities for Boltz service."""

import asyncio
import os
import psutil
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List, Optional

import torch

from boltz_service.config.base import AcceleratorConfig
from boltz_service.utils.errors import ResourceExhaustedError
from boltz_service.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class ResourceStats:
    """Resource statistics."""
    
    cpu_percent: float
    memory_percent: float
    gpu_utilization: Optional[List[float]] = None
    gpu_memory_utilization: Optional[List[float]] = None

class ResourceMonitor:
    """Monitor system resources."""
    
    def __init__(self, interval: int = 5):
        """Initialize resource monitor.
        
        Parameters
        ----------
        interval : int
            Monitoring interval in seconds
        """
        self.interval = interval
        self._stop_event = threading.Event()
        self._stats: Optional[ResourceStats] = None
        self._lock = threading.Lock()
        
    def start(self):
        """Start monitoring resources."""
        def _monitor():
            while not self._stop_event.is_set():
                try:
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_percent = psutil.virtual_memory().percent
                    
                    gpu_utils = None
                    gpu_memory_utils = None
                    
                    if torch.cuda.is_available():
                        gpu_utils = []
                        gpu_memory_utils = []
                        for i in range(torch.cuda.device_count()):
                            # Note: This requires nvidia-smi
                            try:
                                gpu_utils.append(torch.cuda.utilization(i))
                                gpu_memory_utils.append(torch.cuda.memory_allocated(i) / torch.cuda.max_memory_allocated(i) * 100)
                            except Exception:
                                gpu_utils.append(0.0)
                                gpu_memory_utils.append(0.0)
                                
                    with self._lock:
                        self._stats = ResourceStats(
                            cpu_percent=cpu_percent,
                            memory_percent=memory_percent,
                            gpu_utilization=gpu_utils,
                            gpu_memory_utilization=gpu_memory_utils
                        )
                        
                except Exception as e:
                    logger.error(f"Error monitoring resources: {e}")
                    
                self._stop_event.wait(self.interval)
                
        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()
        
    def stop(self):
        """Stop monitoring resources."""
        self._stop_event.set()
        self._monitor_thread.join()
        
    @property
    def stats(self) -> Optional[ResourceStats]:
        """Get current resource statistics."""
        with self._lock:
            return self._stats

class ResourceManager:
    """Manage compute resources."""
    
    def __init__(self, config: AcceleratorConfig):
        """Initialize resource manager.
        
        Parameters
        ----------
        config : AcceleratorConfig
            Accelerator configuration
        """
        self.config = config
        self.monitor = ResourceMonitor()
        self.monitor.start()
        
        self._device_locks: Dict[int, asyncio.Lock] = {}
        self._pool = ThreadPoolExecutor(max_workers=os.cpu_count())
        
        # Initialize device locks
        if config.type == "gpu" and torch.cuda.is_available():
            for device_id in config.device_ids:
                if device_id >= torch.cuda.device_count():
                    raise ValueError(f"Invalid GPU device ID: {device_id}")
                self._device_locks[device_id] = asyncio.Lock()
                
    async def acquire_device(self, device_id: int) -> bool:
        """Acquire a device lock.
        
        Parameters
        ----------
        device_id : int
            Device ID to acquire
            
        Returns
        -------
        bool
            True if device was acquired
            
        Raises
        ------
        ResourceExhaustedError
            If device is not available
        """
        if device_id not in self._device_locks:
            raise ResourceExhaustedError(f"Device {device_id} not available")
            
        # Check resource utilization
        stats = self.monitor.stats
        if stats:
            if self.config.type == "gpu" and stats.gpu_utilization:
                if stats.gpu_utilization[device_id] > 90:
                    raise ResourceExhaustedError(f"GPU {device_id} is overloaded")
                    
            if stats.memory_percent > 90:
                raise ResourceExhaustedError("System memory is exhausted")
                
        # Try to acquire lock
        try:
            await asyncio.wait_for(self._device_locks[device_id].acquire(), timeout=5.0)
            return True
        except asyncio.TimeoutError:
            raise ResourceExhaustedError(f"Timeout waiting for device {device_id}")
            
    def release_device(self, device_id: int):
        """Release a device lock.
        
        Parameters
        ----------
        device_id : int
            Device ID to release
        """
        if device_id in self._device_locks:
            self._device_locks[device_id].release()
            
    def cleanup(self):
        """Clean up resources."""
        self.monitor.stop()
        self._pool.shutdown()
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
    def __del__(self):
        """Clean up on deletion."""
        self.cleanup()
