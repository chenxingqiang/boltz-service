"""
Boltz训练服务实现
"""
import logging
import os
from concurrent import futures
from typing import Dict, Optional
import json

import grpc
import torch
import pytorch_lightning as pl
from mashumaro import DataClassDictMixin
from dataclasses import dataclass
import wandb
from pathlib import Path

from boltz_service.data.module.training import BoltzTrainingDataModule
from boltz_service.model.model import BoltzModel

# 生成的proto代码
from boltz_service.protos import training_service_pb2
from boltz_service.protos import training_service_pb2_grpc
from boltz_service.protos import common_pb2
from boltz_service.data.types import ServiceConfig

logger = logging.getLogger(__name__)

@dataclass
class TrainingJob(DataClassDictMixin):
    """训练任务"""
    job_id: str
    config_path: str
    args: list
    num_gpus: int
    output_dir: str
    resume: bool
    checkpoint: Optional[str]
    experiment_name: str
    hyperparameters: Dict[str, str]
    status: str = "pending"
    current_epoch: float = 0
    val_loss: float = float("inf")
    train_loss: float = float("inf")
    checkpoint_path: Optional[str] = None
    error_message: Optional[str] = None

class TrainingService(training_service_pb2_grpc.TrainingServiceServicer):
    """训练服务实现"""
    
    def __init__(
            self,
            config: ServiceConfig
        ):
        """初始化训练服务

        Args:
            config: 服务配置
        """
        self.data_path = config.data_path
        self.checkpoint_path = config.checkpoint_path
        self.model_path = config.model_path
        
        # 训练任务队列
        self.jobs: Dict[str, TrainingJob] = {}
        # 当前运行的任务
        self.current_job: Optional[str] = None

    def StartTraining(
        self,
        request: training_service_pb2.TrainingRequest,
        context: grpc.ServicerContext
    ) -> training_service_pb2.TrainingResponse:
        """启动训练任务"""
        # 检查任务是否已存在
        if request.job_id in self.jobs:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(f"Job {request.job_id} already exists")
            return training_service_pb2.TrainingResponse(
                job_id=request.job_id,
                status="failed",
                error_message="Job already exists"
            )
            
        # 创建任务
        job = TrainingJob(
            job_id=request.job_id,
            config_path=request.config_path,
            args=request.args,
            num_gpus=request.num_gpus,
            output_dir=request.output_dir,
            resume=request.resume,
            checkpoint=request.checkpoint,
            experiment_name=request.experiment_name,
            hyperparameters=dict(request.hyperparameters)
        )
        self.jobs[job.job_id] = job
        
        # 异步执行训练
        future = self._train_async(job)
        future.add_done_callback(
            lambda f: self._handle_training_complete(job.job_id, f)
        )
        
        return training_service_pb2.TrainingResponse(
            job_id=job.job_id,
            status="started"
        )
            
    def GetTrainingStatus(
        self,
        request: common_pb2.JobStatusRequest,
        context: grpc.ServicerContext
    ) -> training_service_pb2.TrainingJobStatusResponse:
        """获取训练状态"""
        job = self.jobs.get(request.job_id)
        if not job:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Job {request.job_id} not found")
            return training_service_pb2.TrainingJobStatusResponse()

        # 构建基础状态响应
        base_status = common_pb2.JobStatusResponse(
            job_id=job.job_id,
            status=job.status,
            error_message=job.error_message
        )

        # 返回训练特定状态
        return training_service_pb2.TrainingJobStatusResponse(
            base=base_status,
            current_epoch=job.current_epoch,
            val_loss=job.val_loss,
            train_loss=job.train_loss,
            checkpoint_path=job.checkpoint_path,
            error_message=job.error_message
        )
        
    def CancelJob(
        self,
        request: common_pb2.CancelJobRequest,
        context: grpc.ServicerContext
    ) -> training_service_pb2.TrainingResponse:
        """停止训练"""
        if not self.current_job or request.job_id != self.current_job:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No active job to cancel")
            return training_service_pb2.TrainingResponse(
                job_id=request.job_id,
                status="failed",
                error_message="No active job to cancel"
            )
            
        # 停止训练
        job = self.jobs[request.job_id]
        job.status = "cancelled"
        
        return training_service_pb2.TrainingResponse(
            job_id=request.job_id,
            status="cancelled"
        )
            
    def ExportModel(
        self,
        request: training_service_pb2.ExportModelRequest,
        context: grpc.ServicerContext
    ) -> training_service_pb2.ExportModelResponse:
        """导出模型"""
        job = self.jobs.get(request.job_id)
        if not job:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Job {request.job_id} not found")
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id,
                status="not_found"
            )

        # 检查是否有checkpoint
        if not job.checkpoint_path:
            context.set_code(grpc.StatusCode.FAILED_PRECONDITION)
            context.set_details("No checkpoint available")
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id,
                status="failed",
                error_message="No checkpoint available"
            )

        try:
            # 加载模型
            model = BoltzModel.load_from_checkpoint(job.checkpoint_path)
            
            # 导出模型
            output_path = Path(request.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 根据格式导出
            if request.format == "onnx":
                model.to_onnx(output_path)
            elif request.format == "torchscript":
                model.to_torchscript(output_path)
            else:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(f"Unsupported format: {request.format}")
                return training_service_pb2.ExportModelResponse(
                    job_id=request.job_id,
                    status="failed",
                    error_message=f"Unsupported format: {request.format}"
                )
                
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id,
                status="success",
                model_path=str(output_path)
            )
            
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return training_service_pb2.ExportModelResponse(
                job_id=request.job_id,
                status="failed",
                error_message=str(e)
            )

    def _train_async(self, job: TrainingJob) -> futures.Future:
        """异步执行训练"""
        future = futures.Future()
        thread = futures.ThreadPoolExecutor(max_workers=1)
        future = thread.submit(self._train, job)
        return future

    def _train(self, job: TrainingJob):
        """执行训练"""
        try:
            # 设置当前任务
            self.current_job = job.job_id
            job.status = "running"
            
            # 初始化wandb
            wandb.init(
                project="boltz",
                name=job.experiment_name,
                config=job.hyperparameters
            )
            
            # 创建数据模块
            datamodule = BoltzTrainingDataModule(
                cfg=job.hyperparameters
            )
            
            # 创建或加载模型
            if job.resume and job.checkpoint:
                model = BoltzModel.load_from_checkpoint(
                    job.checkpoint,
                    **job.hyperparameters
                )
            else:
                model = BoltzModel(**job.hyperparameters)
                
            # 创建训练器
            trainer = pl.Trainer(
                default_root_dir=job.output_dir,
                devices=job.num_gpus,
                accelerator="gpu",
                callbacks=[self._create_status_callback(job)],
                **job.hyperparameters
            )
            
            # 开始训练
            trainer.fit(model, datamodule)
            
            # 更新状态
            job.status = "completed"
            job.checkpoint_path = trainer.checkpoint_callback.best_model_path
            
        except Exception as e:
            logger.exception("Training failed")
            job.status = "failed"
            job.error_message = str(e)
            raise
            
        finally:
            # 清理当前任务
            if self.current_job == job.job_id:
                self.current_job = None
            wandb.finish()
            
    def _create_status_callback(self, job: TrainingJob):
        """创建状态更新回调"""
        class StatusCallback(pl.Callback):
            def on_train_epoch_end(self, trainer, pl_module):
                job.current_epoch = trainer.current_epoch
                job.train_loss = float(trainer.callback_metrics.get("train_loss", float("inf")))
                job.val_loss = float(trainer.callback_metrics.get("val_loss", float("inf")))
                
            def on_exception(self, trainer, pl_module, exception):
                job.status = "failed"
                job.error_message = str(exception)
                
        return StatusCallback()
        
    def _handle_training_complete(
            self,
            job_id: str,
            future: futures.Future
        ):
        """处理训练完成回调"""
        try:
            future.result()
        except Exception as e:
            logger.exception("Training failed")
            job = self.jobs.get(job_id)
            if job:
                job.status = "failed"
                job.error_message = str(e)

def serve(
    port: int,
    config: ServiceConfig
):
    """启动服务"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    training_service_pb2_grpc.add_TrainingServiceServicer_to_server(
        TrainingService(
            config=config
        ),
        server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()
