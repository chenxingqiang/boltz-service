"""Shared pytest configuration and fixtures."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from unittest import mock

import grpc
import pytest
import torch
import torch.nn as nn
import pytorch_lightning as pl
from grpc_health.v1 import health_pb2, health_pb2_grpc

os.environ.setdefault("no_proxy", "127.0.0.1,0.0.0.0,localhost")
os.environ.setdefault("NO_PROXY", "127.0.0.1,0.0.0.0,localhost")
os.environ.setdefault("http_proxy", "")
os.environ.setdefault("https_proxy", "")
os.environ.setdefault("HTTP_PROXY", "")
os.environ.setdefault("HTTPS_PROXY", "")
os.environ.setdefault("SKIP_BFD_CHECK", "true")

TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_CACHE_DIR = Path(__file__).parent / "data" / "cache"
TEST_PORT = 50052


class MockMSAModule(nn.Module):
    def __init__(self, msa_s=32, msa_blocks=2, msa_dropout=0.1, z_dropout=0.1):
        super().__init__()
        self.encoder = nn.Linear(msa_s, msa_s)
        self.dropout = nn.Dropout(msa_dropout)

    def forward(self, x):
        return self.dropout(self.encoder(x))


class MockPairformerModule(nn.Module):
    def __init__(self, num_blocks, num_layers, num_heads, hidden_size):
        super().__init__()
        self.encoder = nn.Linear(hidden_size, hidden_size)
        self.attention = nn.MultiheadAttention(
            hidden_size, num_heads, batch_first=True
        )
        self.norm = nn.LayerNorm(hidden_size)

    def forward(self, x):
        x = self.encoder(x)
        x = self.attention(x, x, x)[0]
        return self.norm(x)


class MockBoltzModel(pl.LightningModule):
    """Lightweight BoltzModel stand-in for server tests."""

    def __init__(
        self,
        atom_s=64,
        atom_z=32,
        token_s=128,
        token_z=64,
        num_bins=50,
        training_args=None,
        validation_args=None,
        embedder_args=None,
        msa_args=None,
        pairformer_args=None,
        score_model_args=None,
        diffusion_process_args=None,
        diffusion_loss_args=None,
        confidence_model_args=None,
        atom_feature_dim=128,
        confidence_prediction=False,
        confidence_imitate_trunk=False,
        alpha_pae=0.0,
        structure_prediction_training=True,
        atoms_per_window_queries=32,
        atoms_per_window_keys=128,
        compile_pairformer=False,
        compile_structure=False,
        compile_confidence=False,
        nucleotide_rmsd_weight=5.0,
        ligand_rmsd_weight=10.0,
        no_msa=False,
        no_atom_encoder=False,
        ema=False,
        ema_decay=0.999,
        min_dist=2.0,
        max_dist=22.0,
        predict_args=None,
    ):
        super().__init__()
        self.save_hyperparameters()
        self.hparams.training_args = training_args or {"batch_size": 2}
        self.hparams.validation_args = validation_args or {"val_check_interval": 1.0}
        self.hparams.embedder_args = embedder_args or {
            "atom_encoder_depth": 3,
            "atom_encoder_heads": 4,
            "atoms_per_window_queries": 32,
            "atoms_per_window_keys": 128,
            "atom_feature_dim": 128,
            "no_atom_encoder": False,
        }
        self.hparams.msa_args = msa_args or {
            "num_sequences": 10,
            "msa_s": 32,
            "msa_blocks": 2,
            "msa_dropout": 0.1,
            "z_dropout": 0.1,
        }
        self.hparams.pairformer_args = pairformer_args or {
            "num_layers": 2,
            "num_blocks": 4,
            "num_heads": 4,
            "hidden_size": 32,
        }
        self.hparams.score_model_args = score_model_args or {"hidden_size": 64}
        self.hparams.diffusion_process_args = diffusion_process_args or {
            "num_steps": 100
        }
        self.hparams.diffusion_loss_args = diffusion_loss_args or {"loss_type": "l2"}
        self.hparams.confidence_model_args = confidence_model_args or {
            "hidden_size": 32
        }
        msa_config = {
            k: self.hparams.msa_args[k]
            for k in ("msa_s", "msa_blocks", "msa_dropout", "z_dropout")
        }
        pairformer_config = {
            k: self.hparams.pairformer_args[k]
            for k in ("num_blocks", "num_layers", "num_heads", "hidden_size")
        }
        self.msa_module = MockMSAModule(**msa_config)
        self.pairformer = MockPairformerModule(**pairformer_config)
        self.trunk = nn.Linear(32, 32)
        self.head = nn.Linear(32, 32)

    def forward(self, batch):
        return {
            "predicted_coords": torch.randn(1, 10, 3),
            "predicted_lddt": torch.rand(1, 10),
            "predicted_plddt": torch.rand(1, 10),
            "predicted_positions": torch.randn(1, 10, 3),
        }

    def predict(self, datamodule, recycling_steps=1, sampling_steps=10, diffusion_samples=1):
        del datamodule, recycling_steps, sampling_steps, diffusion_samples
        return [{"prediction": "mock"}]

    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.001)

    def state_dict(self):
        return {
            "msa_module.encoder.weight": torch.randn(32, 32),
            "msa_module.encoder.bias": torch.randn(32),
            "pairformer.encoder.weight": torch.randn(32, 32),
            "pairformer.encoder.bias": torch.randn(32),
            "pairformer.attention.in_proj_weight": torch.randn(96, 32),
            "pairformer.attention.in_proj_bias": torch.randn(96),
            "pairformer.attention.out_proj.weight": torch.randn(32, 32),
            "pairformer.attention.out_proj.bias": torch.randn(32),
            "pairformer.norm.weight": torch.randn(32),
            "pairformer.norm.bias": torch.randn(32),
            "trunk.weight": torch.randn(32, 32),
            "trunk.bias": torch.randn(32),
            "head.weight": torch.randn(32, 32),
            "head.bias": torch.randn(32),
        }

    def load_state_dict(self, state_dict, strict=True):
        del strict
        for name, param in state_dict.items():
            parts = name.split(".")
            module = self
            for part in parts[:-1]:
                module = getattr(module, part)
            target = getattr(module, parts[-1])
            if hasattr(target, "data"):
                target.data.copy_(param)
            elif parts[-1] == "p":
                module.p = param.item()

    @classmethod
    def load_from_checkpoint(cls, checkpoint_path, map_location=None):
        del map_location
        checkpoint = torch.load(checkpoint_path, weights_only=False)
        model = cls(**checkpoint.get("hyper_parameters", {}))
        model.load_state_dict(checkpoint["state_dict"])
        return model


def _fake_run_prediction(self, job):
    output_dir = Path(self.cache_dir) / "predictions" / job.job_id
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"prediction.{job.output_format}"
    output_path.write_text("HEADER\n", encoding="utf-8")
    return str(output_path)


async def _fake_run_hhblits(self, sequence, output_path, options):
    del self, options
    Path(output_path).write_text(f">query\n{sequence}\n", encoding="utf-8")


def _fake_train(self, job):
    job.status = "completed"
    job.checkpoint_path = str(Path(job.output_dir) / "checkpoint.ckpt")
    Path(job.output_dir).mkdir(parents=True, exist_ok=True)
    Path(job.checkpoint_path).write_text("mock-checkpoint", encoding="utf-8")


def _ensure_service_modules_loaded() -> None:
    import importlib
    import sys
    import types

    if "wandb" not in sys.modules:
        wandb_stub = types.ModuleType("wandb")
        wandb_stub.init = lambda *args, **kwargs: None
        sys.modules["wandb"] = wandb_stub

    for module_name in (
        "boltz_service.model.model",
        "boltz_service.services.inference",
        "boltz_service.services.training",
        "boltz_service.services.msa",
        "boltz_service.utils.db_manager",
    ):
        importlib.import_module(module_name)


@pytest.fixture(scope="module")
def mock_boltz_model():
    _ensure_service_modules_loaded()
    with mock.patch("boltz_service.model.model.BoltzModel", MockBoltzModel), mock.patch(
        "boltz_service.services.inference.BoltzModel", MockBoltzModel
    ), mock.patch("boltz_service.services.training.BoltzModel", MockBoltzModel), mock.patch(
        "boltz_service.utils.db_manager.DatabaseManager.check_database_health",
        return_value=[],
    ), mock.patch(
        "boltz_service.services.inference.InferenceService._run_prediction",
        _fake_run_prediction,
    ), mock.patch(
        "boltz_service.services.msa.MSAService._run_hhblits",
        _fake_run_hhblits,
    ), mock.patch(
        "boltz_service.services.training.TrainingService._train",
        _fake_train,
    ), mock.patch("boltz_service.services.training.wandb.init"):
        yield MockBoltzModel


@pytest.fixture(scope="module")
def setup_test_dirs(mock_boltz_model):
    del mock_boltz_model
    if TEST_DATA_DIR.exists():
        shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)

    model_dir = TEST_CACHE_DIR / "models" / "v1"
    model_dir.mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "training").mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "checkpoints").mkdir(parents=True, exist_ok=True)

    model = MockBoltzModel()
    checkpoint = {
        "epoch": 0,
        "global_step": 0,
        "pytorch-lightning_version": "2.0.0",
        "state_dict": model.state_dict(),
        "hyper_parameters": dict(model.hparams),
    }
    torch.save(checkpoint, model_dir / "model.ckpt")

    yield

    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)


def _release_port(port: int) -> None:
    output = subprocess.run(
        ["lsof", "-t", "-i", f":{port}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if output.stdout.strip():
        subprocess.run(
            ["kill", "-9", *output.stdout.strip().split()],
            capture_output=True,
            check=False,
        )
        time.sleep(1)


def _wait_for_server(port: int, retries: int = 10) -> None:
    for retry in range(retries):
        try:
            channel = grpc.insecure_channel(f"127.0.0.1:{port}")
            grpc.channel_ready_future(channel).result(timeout=2)
            health_stub = health_pb2_grpc.HealthStub(channel)
            response = health_stub.Check(health_pb2.HealthCheckRequest(), timeout=1)
            if response.status == health_pb2.HealthCheckResponse.SERVING:
                return
        except (grpc.FutureTimeoutError, grpc.RpcError):
            if retry == retries - 1:
                raise
            time.sleep(0.5 * (2**retry))


@pytest.fixture(scope="module")
def grpc_server(mock_boltz_model, setup_test_dirs):
    del mock_boltz_model, setup_test_dirs
    from boltz_service.config.base import BaseConfig
    from boltz_service.main import BoltzServer

    _release_port(TEST_PORT)

    config = BaseConfig()
    config.network.host = "127.0.0.1"
    config.network.port = TEST_PORT
    config.network.max_workers = 2
    config.accelerator.type = "cpu"
    config.accelerator.device_ids = [0]
    config.cache.cache_dir = TEST_CACHE_DIR

    server = BoltzServer(config)
    server.start()
    _wait_for_server(TEST_PORT)

    yield server

    try:
        server.stop()
    except Exception:
        pass
    _release_port(TEST_PORT)


@pytest.fixture(scope="module")
def inference_stub(grpc_server):
    del grpc_server
    from boltz_service.protos import inference_service_pb2_grpc

    channel = grpc.insecure_channel(f"127.0.0.1:{TEST_PORT}")
    return inference_service_pb2_grpc.InferenceServiceStub(channel)


@pytest.fixture(scope="module")
def msa_stub(grpc_server):
    del grpc_server
    from boltz_service.protos import msa_service_pb2_grpc

    channel = grpc.insecure_channel(f"127.0.0.1:{TEST_PORT}")
    return msa_service_pb2_grpc.MSAServiceStub(channel)


@pytest.fixture(scope="module")
def training_stub(grpc_server):
    del grpc_server
    from boltz_service.protos import training_service_pb2_grpc

    channel = grpc.insecure_channel(f"127.0.0.1:{TEST_PORT}")
    return training_service_pb2_grpc.TrainingServiceStub(channel)
