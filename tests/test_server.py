"""
Test the Boltz gRPC server implementation
"""
import os
import time
import torch
import torch.nn as nn
import pytorch_lightning as pl
import pytest
from pathlib import Path
import shutil
import grpc
import unittest.mock as mock

# Disable proxy for localhost connections
os.environ["no_proxy"] = "127.0.0.1,0.0.0.0"
os.environ["NO_PROXY"] = "127.0.0.1,0.0.0.0"
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

from boltz_service.protos import inference_service_pb2, inference_service_pb2_grpc
from boltz_service.protos import msa_service_pb2, msa_service_pb2_grpc
from boltz_service.protos import training_service_pb2, training_service_pb2_grpc
from boltz_service.protos import common_pb2
from boltz_service.services.server import BoltzServer
from boltz_service.data.types import ServiceConfig

# Mock MSA module
class MockMSAModule(nn.Module):
    def __init__(self, msa_s=32, msa_blocks=2, msa_dropout=0.1, z_dropout=0.1):
        super().__init__()
        self.msa_s = msa_s
        self.msa_blocks = msa_blocks
        self.msa_dropout = msa_dropout
        self.z_dropout = z_dropout
        
        # Add some mock layers
        self.encoder = nn.Linear(msa_s, msa_s)
        self.dropout = nn.Dropout(msa_dropout)
        
    def forward(self, x):
        # Mock MSA processing
        x = self.encoder(x)
        x = self.dropout(x)
        return x

class MockPairformerModule(nn.Module):
    """Mock pairformer module for testing"""
    def __init__(self, num_blocks, num_layers, num_heads, hidden_size):
        super().__init__()
        self.num_blocks = num_blocks
        self.num_layers = num_layers
        self.num_heads = num_heads
        self.hidden_size = hidden_size
        
        self.encoder = nn.Linear(hidden_size, hidden_size)
        self.attention = nn.MultiheadAttention(hidden_size, num_heads, batch_first=True)
        self.norm = nn.LayerNorm(hidden_size)
        
    def forward(self, x):
        # Mock pairformer processing
        x = self.encoder(x)
        x = self.attention(x, x, x)[0]
        return self.norm(x)

class MockBoltzModel(pl.LightningModule):
    """Mock model for testing"""
    def __init__(self, atom_s=64, atom_z=32, token_s=128, token_z=64, num_bins=50,
                 training_args=None, validation_args=None, embedder_args=None,
                 msa_args=None, pairformer_args=None, score_model_args=None,
                 diffusion_process_args=None, diffusion_loss_args=None,
                 confidence_model_args=None, atom_feature_dim=128,
                 confidence_prediction=False, confidence_imitate_trunk=False,
                 alpha_pae=0.0, structure_prediction_training=True,
                 atoms_per_window_queries=32, atoms_per_window_keys=128,
                 compile_pairformer=False, compile_structure=False,
                 compile_confidence=False, nucleotide_rmsd_weight=5.0,
                 ligand_rmsd_weight=10.0, no_msa=False, no_atom_encoder=False,
                 ema=False, ema_decay=0.999, min_dist=2.0, max_dist=22.0,
                 predict_args=None):
        super().__init__()
        
        # Save all arguments as hyperparameters
        self.save_hyperparameters()
        
        # Set default args if not provided
        self.hparams.training_args = training_args or {"batch_size": 2}
        self.hparams.validation_args = validation_args or {"val_check_interval": 1.0}
        self.hparams.embedder_args = embedder_args or {
            "atom_encoder_depth": 3,
            "atom_encoder_heads": 4,
            "atoms_per_window_queries": 32,
            "atoms_per_window_keys": 128,
            "atom_feature_dim": 128,
            "no_atom_encoder": False
        }
        self.hparams.msa_args = msa_args or {
            "num_sequences": 10,
            "msa_s": 32,
            "msa_blocks": 2,
            "msa_dropout": 0.1,
            "z_dropout": 0.1
        }
        self.hparams.pairformer_args = pairformer_args or {
            "num_layers": 2,
            "num_blocks": 4,
            "num_heads": 4,
            "hidden_size": 32
        }
        self.hparams.score_model_args = score_model_args or {"hidden_size": 64}
        self.hparams.diffusion_process_args = diffusion_process_args or {"num_steps": 100}
        self.hparams.diffusion_loss_args = diffusion_loss_args or {"loss_type": "l2"}
        self.hparams.confidence_model_args = confidence_model_args or {"hidden_size": 32}
        
        # Add required modules
        msa_config = {
            'msa_s': self.hparams.msa_args['msa_s'],
            'msa_blocks': self.hparams.msa_args['msa_blocks'],
            'msa_dropout': self.hparams.msa_args['msa_dropout'],
            'z_dropout': self.hparams.msa_args['z_dropout']
        }
        self.msa_module = MockMSAModule(**msa_config)
        
        # Initialize pairformer with required num_blocks
        pairformer_config = {
            'num_blocks': self.hparams.pairformer_args['num_blocks'],
            'num_layers': self.hparams.pairformer_args['num_layers'],
            'num_heads': self.hparams.pairformer_args['num_heads'],
            'hidden_size': self.hparams.pairformer_args['hidden_size']
        }
        self.pairformer = MockPairformerModule(**pairformer_config)
        
        self.trunk = nn.Linear(32, 32)  # Mock trunk
        self.head = nn.Linear(32, 32)   # Mock head
        
        # Add metrics for confidence prediction
        if confidence_prediction:
            self.lddt = nn.ModuleDict()
            self.disto_lddt = nn.ModuleDict()
            self.complex_lddt = nn.ModuleDict()
            self.top1_lddt = nn.ModuleDict()
            self.iplddt_top1_lddt = nn.ModuleDict()
            self.ipde_top1_lddt = nn.ModuleDict()
            self.pde_top1_lddt = nn.ModuleDict()
            self.ptm_top1_lddt = nn.ModuleDict()
            self.iptm_top1_lddt = nn.ModuleDict()
            self.ligand_iptm_top1_lddt = nn.ModuleDict()
            self.protein_iptm_top1_lddt = nn.ModuleDict()
            self.avg_lddt = nn.ModuleDict()
            self.plddt_mae = nn.ModuleDict()
            self.pde_mae = nn.ModuleDict()
            self.pae_mae = nn.ModuleDict()
        
    def forward(self, batch):
        # Return mock prediction data
        return {
            'predicted_coords': torch.randn(1, 10, 3),
            'predicted_lddt': torch.rand(1, 10),
            'predicted_plddt': torch.rand(1, 10),
            'predicted_positions': torch.randn(1, 10, 3),
        }
        
    def configure_optimizers(self):
        return torch.optim.Adam(self.parameters(), lr=0.001)
        
    def state_dict(self):
        # Return a minimal state dict for testing
        return {
            'msa_module.encoder.weight': torch.randn(32, 32),
            'msa_module.encoder.bias': torch.randn(32),
            'msa_module.dropout.p': torch.tensor(0.1),
            'pairformer.encoder.weight': torch.randn(32, 32),
            'pairformer.encoder.bias': torch.randn(32),
            'pairformer.attention.in_proj_weight': torch.randn(96, 32),
            'pairformer.attention.in_proj_bias': torch.randn(96),
            'pairformer.attention.out_proj.weight': torch.randn(32, 32),
            'pairformer.attention.out_proj.bias': torch.randn(32),
            'pairformer.norm.weight': torch.randn(32),
            'pairformer.norm.bias': torch.randn(32),
            'trunk.weight': torch.randn(32, 32),
            'trunk.bias': torch.randn(32),
            'head.weight': torch.randn(32, 32),
            'head.bias': torch.randn(32),
        }
        
    def load_state_dict(self, state_dict):
        # Properly load the state dict
        for name, param in state_dict.items():
            if name == 'msa_module.encoder.weight':
                self.msa_module.encoder.weight.data.copy_(param)
            elif name == 'msa_module.encoder.bias':
                self.msa_module.encoder.bias.data.copy_(param)
            elif name == 'msa_module.dropout.p':
                self.msa_module.dropout.p = param.item()
            elif name == 'pairformer.encoder.weight':
                self.pairformer.encoder.weight.data.copy_(param)
            elif name == 'pairformer.encoder.bias':
                self.pairformer.encoder.bias.data.copy_(param)
            elif name == 'pairformer.attention.in_proj_weight':
                self.pairformer.attention.in_proj_weight.data.copy_(param)
            elif name == 'pairformer.attention.in_proj_bias':
                self.pairformer.attention.in_proj_bias.data.copy_(param)
            elif name == 'pairformer.attention.out_proj.weight':
                self.pairformer.attention.out_proj.weight.data.copy_(param)
            elif name == 'pairformer.attention.out_proj.bias':
                self.pairformer.attention.out_proj.bias.data.copy_(param)
            elif name == 'pairformer.norm.weight':
                self.pairformer.norm.weight.data.copy_(param)
            elif name == 'pairformer.norm.bias':
                self.pairformer.norm.bias.data.copy_(param)
            elif name == 'trunk.weight':
                self.trunk.weight.data.copy_(param)
            elif name == 'trunk.bias':
                self.trunk.bias.data.copy_(param)
            elif name == 'head.weight':
                self.head.weight.data.copy_(param)
            elif name == 'head.bias':
                self.head.bias.data.copy_(param)
        
    @classmethod
    def load_from_checkpoint(cls, checkpoint_path, map_location=None):
        checkpoint = torch.load(checkpoint_path, map_location=map_location)
        model = cls(**checkpoint.get('hyper_parameters', {}))
        model.load_state_dict(checkpoint['state_dict'])
        return model

# Apply mock
@pytest.fixture(autouse=True)
def mock_boltz_model():
    """Mock BoltzModel for testing"""
    with mock.patch('boltz_service.model.model.BoltzModel', MockBoltzModel), \
         mock.patch('boltz_service.services.inference.BoltzModel', MockBoltzModel):
        yield

@pytest.fixture(scope="module")
def mock_model():
    """Create mock model checkpoint"""
    model = MockBoltzModel()
    return model

@pytest.fixture(scope="module", autouse=True)
def setup_test_dirs(mock_model):
    """Setup test directories"""
    # Create test directories
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEST_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (TEST_DATA_DIR / "training").mkdir(exist_ok=True)
    (TEST_DATA_DIR / "checkpoints").mkdir(exist_ok=True)
    model_dir = TEST_CACHE_DIR 
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Create and save mock model
    model = mock_model
    checkpoint = {
        'epoch': 0,
        'global_step': 0,
        'pytorch-lightning_version': '2.0.0',
        'state_dict': model.state_dict(),
        'hyper_parameters': model.hparams
    }
    
    # Save checkpoint
    checkpoint_path = model_dir / "model.ckpt"
    torch.save(checkpoint, checkpoint_path)
    
    # Verify checkpoint exists
    if not checkpoint_path.exists():
        raise RuntimeError(f"Failed to create mock model checkpoint at {checkpoint_path}")
    
    yield
    
    # Cleanup test directories
    shutil.rmtree(TEST_DATA_DIR, ignore_errors=True)
    shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)

@pytest.fixture(scope="module")
def server():
    """Start test server"""
    # Kill any existing process on the test port
    import subprocess
    subprocess.run(['lsof', '-t', '-i', f':{TEST_PORT}'], capture_output=True)
    output = subprocess.run(['lsof', '-t', '-i', f':{TEST_PORT}'], capture_output=True)
    if output.stdout:
        pid = output.stdout.decode().strip()
        subprocess.run(['kill', '-9', pid], capture_output=True)
        time.sleep(1)  # Wait for port to be released
    
    # Create test config
    config = ServiceConfig(
        cache_dir=TEST_CACHE_DIR,
        data_path=TEST_DATA_DIR / "training",
        checkpoint_path=TEST_DATA_DIR / "checkpoints",
        model_path=TEST_CACHE_DIR / "models",  # Use cache dir for models
        devices=1,
        accelerator="cpu",
        num_workers=2
    )
    
    # Create server
    server = BoltzServer(
        host="127.0.0.1",  # Use explicit IP instead of localhost
        port=TEST_PORT,
        max_workers=2,
        config=config
    )
    
    # Start server in a separate thread
    import threading
    server_thread = threading.Thread(target=server.start)
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start with exponential backoff
    import grpc
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    
    max_retries = 5
    base_delay = 0.5
    for retry in range(max_retries):
        try:
            # Create channel and wait for it to be ready
            channel = grpc.insecure_channel(f'127.0.0.1:{TEST_PORT}')
            grpc.channel_ready_future(channel).result(timeout=2)
            
            # Check health status
            health_stub = health_pb2_grpc.HealthStub(channel)
            request = health_pb2.HealthCheckRequest()
            response = health_stub.Check(request, timeout=1)
            
            if response.status == health_pb2.HealthCheckResponse.SERVING:
                break
        except (grpc.FutureTimeoutError, grpc.RpcError) as e:
            if retry == max_retries - 1:
                server.stop()
                server_thread.join(timeout=5)
                raise RuntimeError(f"Server failed to start after {max_retries} retries: {str(e)}")
            time.sleep(base_delay * (2 ** retry))
    
    # Wait a bit more to ensure server is fully initialized
    time.sleep(1)
    
    yield server
    
    # Cleanup
    try:
        server.stop()
        server_thread.join(timeout=5)
        time.sleep(1)  # Wait for server to fully stop
    except:
        pass  # Ignore cleanup errors

@pytest.fixture(scope="module")
def inference_stub():
    """Create inference service stub"""
    channel = grpc.insecure_channel(f'127.0.0.1:{TEST_PORT}')
    return inference_service_pb2_grpc.InferenceServiceStub(channel)

@pytest.fixture(scope="module")
def msa_stub():
    """Create MSA service stub"""
    channel = grpc.insecure_channel(f'127.0.0.1:{TEST_PORT}')
    return msa_service_pb2_grpc.MSAServiceStub(channel)

@pytest.fixture(scope="module")
def training_stub():
    """Create training service stub"""
    channel = grpc.insecure_channel(f'127.0.0.1:{TEST_PORT}')
    return training_service_pb2_grpc.TrainingServiceStub(channel)

def test_inference_service(inference_stub):
    """Test inference service"""
    # Test sequence prediction
    sequence = "MVKVGVNG"
    request = inference_service_pb2.PredictionRequest(
        sequence=sequence,
        recycling_steps=1,
        sampling_steps=10,
        diffusion_samples=1,
        output_format="pdb"
    )
    
    response = inference_stub.PredictStructure(request)
    assert response.status == common_pb2.Status.SUCCESS
    assert response.message == "Structure prediction completed successfully"
    assert response.output_format == "pdb"
    assert len(response.output_data) > 0

def test_msa_service(msa_stub):
    """Test MSA service"""
    # Test MSA generation
    sequence = "MVKVGVNG"
    request = msa_service_pb2.MSARequest(
        job_id="test_msa_job",
        sequence=sequence,
        max_seqs=10,
        min_identity=0.3,
        num_iterations=3
    )
    
    response = msa_stub.GenerateMSA(request)
    assert response.status == common_pb2.Status.SUCCESS
    assert response.message == "MSA generation completed successfully"
    assert len(response.sequences) > 0
    assert len(response.scores) > 0

def test_training_service(training_stub):
    """Test training service"""
    # Create test config file
    config_file = TEST_DATA_DIR / "test_config.yaml"
    with open(config_file, "w") as f:
        f.write("""
version: 1
model:
  name: test_model
  hidden_size: 32
  num_layers: 2
training:
  batch_size: 2
  max_epochs: 1
  learning_rate: 0.001
""")
    
    # Start training
    request = training_service_pb2.TrainingRequest(
        job_id="test_job",
        config_path=str(config_file),
        num_gpus=1,
        output_dir=str(TEST_DATA_DIR / "output"),
        experiment_name="test_experiment",
        hyperparameters={
            "batch_size": "2",
            "max_epochs": "1"
        }
    )
    
    response = training_stub.StartTraining(request)
    assert response.status == common_pb2.Status.SUCCESS
    assert response.message == "Training job started successfully"
    assert response.job_id == "test_job"

def test_health_check(server):
    """Test health checking"""
    from grpc_health.v1 import health_pb2, health_pb2_grpc
    
    channel = grpc.insecure_channel(f'127.0.0.1:{TEST_PORT}')
    health_stub = health_pb2_grpc.HealthStub(channel)
    
    # Check overall health
    request = health_pb2.HealthCheckRequest()
    response = health_stub.Check(request)
    assert response.status == health_pb2.HealthCheckResponse.SERVING

TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_CACHE_DIR = Path.home() / ".boltz"  # Use ~/.boltz as cache dir
TEST_PORT = 50052  # Use a different port for testing
