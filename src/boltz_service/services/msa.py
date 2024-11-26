import asyncio
import logging
import os
import random
import shutil
import tempfile
import uuid
from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord

from boltz_service.data.parse.a3m import parse_a3m
from boltz_service.protos import msa_service_pb2 as msa_pb2
from boltz_service.protos import msa_service_pb2_grpc as msa_pb2_grpc
from boltz_service.protos import common_pb2
from boltz_service.data.types import ServiceConfig
from boltz_service.utils.database import get_taxonomy_db
from boltz_service.utils.database_config import DatabaseConfig
from boltz_service.utils.db_manager import DatabaseManager
from boltz_service.utils.redis_cache import get_redis_cache
from boltz_service.utils.sequence import validate_sequence

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MSAService(msa_pb2_grpc.MSAServiceServicer):
    """MSA generation service"""
    
    def __init__(self, config: ServiceConfig):
        """Initialize MSA service

        Parameters
        ----------
        config : ServiceConfig
            Service configuration
        """
        self.config = config
        self.cache_dir = config.cache_dir
        self.db_config = DatabaseConfig.from_env()
        self.db_manager = DatabaseManager()
        self._setup_dirs()
        self._check_databases()
        
    def _setup_dirs(self):
        """Set up cache directory"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def _check_databases(self):
        """Check database status"""
        errors = self.db_manager.check_database_health()
        if errors:
            logger.error("Database health check failed:")
            for error in errors:
                logger.error(f"- {error}")
            raise RuntimeError("Database health check failed")
            
    def _cleanup_cache(self):
        """Clean up cache"""
        try:
            self.db_manager.cleanup_cache(
                self.cache_dir,
                max_size=100 * 1024 * 1024 * 1024  # 100GB
            )
        except Exception as e:
            logger.warning(f"Failed to cleanup cache: {e}")
            
    async def _run_hhblits(self, sequence: str, output_path: str, options: dict) -> None:
        """Run HHblits for sequence search
        
        Parameters
        ----------
        sequence : str
            Input sequence
        output_path : str
            Output file path
        options : dict
            HHblits options
            
        """
        # Check cache
        cache = get_redis_cache()
        if cache:
            cached_path = cache.get_msa(sequence)
            if cached_path and os.path.exists(cached_path):
                logger.info(f"Using cached MSA: {cached_path}")
                shutil.copy(cached_path, output_path)
                return
                
        bfd_path = os.getenv("BOLTZ_BFD_PATH")
        skip_bfd = os.getenv("SKIP_BFD_CHECK", "").lower() == "true"

        if not skip_bfd and (not bfd_path or not os.path.exists(bfd_path)):
            raise ValueError(f"BFD database not found at {bfd_path}")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.fasta') as query_file:
            query_file.write(f">query\n{sequence}\n")
            query_file.flush()

            # If skipping BFD, use minimal parameters for testing
            if skip_bfd:
                cmd = [
                    "hhblits",
                    "-i", query_file.name,
                    "-oa3m", output_path,
                    "-n", "1",  # Minimal iterations for testing
                    "-cpu", "1"
                ]
            else:
                cmd = [
                    "hhblits",
                    "-i", query_file.name,
                    "-d", bfd_path,
                    "-oa3m", output_path,
                    "-n", "3",
                    "-cpu", "4"
                ]
            
            # Add additional options
            if options:
                cmd.extend([
                    "-e", "0.001",
                    "-maxseq", str(options["max_seqs"]),
                    "-id", f"{int(options['min_identity']*100)}",
                    "-cov", "70",
                ])
            
            # Run HHblits
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"HHblits failed: {stderr.decode()}")
                
            # Cache result
            if cache:
                cache.set_msa(sequence, output_path)
                
    def GenerateMSA(
        self,
        request: msa_pb2.MSARequest,
        context: grpc.ServicerContext
    ) -> msa_pb2.MSAResponse:
        """Generate MSA for a sequence"""
        try:
            # Validate sequence
            if not validate_sequence(request.sequence):
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid sequence")
                return msa_pb2.MSAResponse()
                
            # Create output directory
            output_dir = os.path.join(self.cache_dir, "msa", request.job_id)
            os.makedirs(output_dir, exist_ok=True)
            
            # Set up HHblits options
            options = {
                "max_seqs": request.max_seqs,
                "min_identity": request.min_identity,
                "num_iterations": request.num_iterations,
            }
            
            # Run HHblits
            output_path = os.path.join(output_dir, "msa.a3m")
            asyncio.run(self._run_hhblits(request.sequence, output_path, options))
            
            return msa_pb2.MSAResponse(
                job_id=request.job_id,
                status="completed",
                result_path=output_path,
            )
            
        except Exception as e:
            logger.error(f"MSA generation failed: {e}")
            return msa_pb2.MSAResponse(
                job_id=request.job_id,
                status="failed",
                error_message=str(e),
            )
            
    def GetJobStatus(
        self,
        request: common_pb2.JobStatusRequest,
        context: grpc.ServicerContext
    ) -> common_pb2.JobStatusResponse:
        """Get job status"""
        # For now, MSA generation is synchronous
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("MSA generation is synchronous")
        return common_pb2.JobStatusResponse()
        
    def CancelJob(
        self,
        request: common_pb2.CancelJobRequest,
        context: grpc.ServicerContext
    ) -> common_pb2.CancelJobResponse:
        """Cancel job"""
        # For now, MSA generation is synchronous
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details("MSA generation is synchronous")
        return common_pb2.CancelJobResponse()


def serve(port: int = 50053, config: ServiceConfig = None):
    """Start service"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    msa_pb2_grpc.add_MSAServiceServicer_to_server(
        MSAService(config=config),
        server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logger.info(f"MSA service started on port {port}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
