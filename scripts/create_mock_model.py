"""Create mock model checkpoint for testing"""
import torch
import torch.nn as nn
from pathlib import Path

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
        
    def forward(self, z, s_inputs, feats):
        # Mock MSA processing
        z = self.encoder(z)
        z = self.dropout(z)
        return z

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
        
    def forward(self, s, z, mask=None, pair_mask=None):
        # Mock pairformer processing
        z = self.encoder(z)
        z = self.attention(z, z, z)[0]
        z = self.norm(z)
        return s, z

class MockStructureModule(nn.Module):
    """Mock structure module for testing"""
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(32, 32)

    def forward(self, s_trunk, z_trunk, s_inputs, feats, relative_position_encoding, multiplicity):
        return {"structure_output": self.linear(s_trunk)}

    def sample(self, s_trunk, z_trunk, s_inputs, feats, relative_position_encoding, num_sampling_steps, atom_mask, multiplicity, train_accumulate_token_repr):
        return {
            "sample_atom_coords": torch.randn(2, 32, 3),
            "diff_token_repr": torch.randn(2, 32, 32) if train_accumulate_token_repr else None
        }

class MockConfidenceModule(nn.Module):
    """Mock confidence module for testing"""
    def __init__(self):
        super().__init__()
        self.use_s_diffusion = True
        self.linear = nn.Linear(32, 32)

    def forward(self, s_inputs, s, z, s_diffusion, x_pred, feats, pred_distogram_logits, multiplicity):
        return {
            "plddt": torch.randn(2, 32),
            "confidence_output": self.linear(s)
        }

class MockDistogramModule(nn.Module):
    """Mock distogram module for testing"""
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(32, 64)  # 64 bins

    def forward(self, z):
        return self.linear(z)

class MockBoltzModel(nn.Module):
    """Mock model for testing"""
    def __init__(self, atom_s=64, atom_z=32, token_s=128, token_z=64, num_bins=50,
                 training_args=None, validation_args=None, embedder_args=None,
                 msa_args=None, pairformer_args=None, score_model_args=None,
                 diffusion_process_args=None, diffusion_loss_args=None,
                 confidence_model_args=None, confidence_prediction=True,
                 structure_prediction_training=True, no_msa=False):
        super().__init__()
        
        # Set default values for required arguments
        self.atom_s = atom_s
        self.atom_z = atom_z
        self.token_s = token_s
        self.token_z = token_z
        self.num_bins = num_bins
        self.training_args = training_args or {"batch_size": 2}
        self.validation_args = validation_args or {"val_check_interval": 1.0}
        self.embedder_args = embedder_args or {
            "atom_encoder_depth": 3,
            "atom_encoder_heads": 4,
            "atoms_per_window_queries": 32,
            "atoms_per_window_keys": 128,
            "atom_feature_dim": 128,
            "no_atom_encoder": False
        }
        self.msa_args = msa_args or {
            "num_sequences": 10,
            "msa_s": 32,
            "msa_blocks": 2,
            "msa_dropout": 0.1,
            "z_dropout": 0.1
        }
        self.pairformer_args = pairformer_args or {
            "num_layers": 2,
            "num_blocks": 4,
            "num_heads": 4,
            "hidden_size": 32
        }
        self.score_model_args = score_model_args or {"hidden_size": 64}
        self.diffusion_process_args = diffusion_process_args or {"num_steps": 100}
        self.diffusion_loss_args = diffusion_loss_args or {"loss_type": "l2"}
        self.confidence_model_args = confidence_model_args or {"hidden_size": 32}
        
        self.confidence_prediction = confidence_prediction
        self.structure_prediction_training = structure_prediction_training
        self.no_msa = no_msa
        self.is_pairformer_compiled = False

        # Input projections
        self.s_init = nn.Linear(32, token_s, bias=False)
        self.z_init_1 = nn.Linear(32, token_z, bias=False)
        self.z_init_2 = nn.Linear(32, token_z, bias=False)
        self.s_recycle = nn.Linear(token_s, token_s, bias=False)
        self.z_recycle = nn.Linear(token_z, token_z, bias=False)
        self.s_norm = nn.LayerNorm(token_s)
        self.z_norm = nn.LayerNorm(token_z)
        
        # Add required modules
        msa_config = {
            'msa_s': self.msa_args['msa_s'],
            'msa_blocks': self.msa_args['msa_blocks'],
            'msa_dropout': self.msa_args['msa_dropout'],
            'z_dropout': self.msa_args['z_dropout']
        }
        self.msa_module = MockMSAModule(**msa_config)
        
        # Initialize pairformer with required num_blocks
        self.pairformer_module = MockPairformerModule(
            num_blocks=self.pairformer_args['num_blocks'],
            num_layers=self.pairformer_args['num_layers'],
            num_heads=self.pairformer_args['num_heads'],
            hidden_size=self.pairformer_args['hidden_size']
        )

        # Additional required modules
        self.structure_module = MockStructureModule()
        self.confidence_module = MockConfidenceModule()
        self.distogram_module = MockDistogramModule()

        # Mock input embedder
        self.input_embedder = nn.Linear(32, token_s)
        self.rel_pos = nn.Linear(32, token_z)
        self.token_bonds = nn.Linear(1, token_z, bias=False)

    def forward(self, batch, recycling_steps=0, num_sampling_steps=None, 
                multiplicity_diffusion_train=1, diffusion_samples=1):
        # Mock forward pass
        s_inputs = self.input_embedder(torch.randn(2, 32, 32))
        s_init = self.s_init(s_inputs)
        z_init = (
            self.z_init_1(s_inputs)[:, :, None] + 
            self.z_init_2(s_inputs)[:, None, :]
        )
        relative_position_encoding = self.rel_pos(torch.randn(2, 32, 32))
        z_init = z_init + relative_position_encoding
        z_init = z_init + self.token_bonds(torch.randn(2, 32, 32, 1))

        s = torch.zeros_like(s_init)
        z = torch.zeros_like(z_init)

        mask = batch.get("token_pad_mask", torch.ones(2, 32)).float()
        pair_mask = mask[:, :, None] * mask[:, None, :]

        for i in range(recycling_steps + 1):
            s = s_init + self.s_recycle(self.s_norm(s))
            z = z_init + self.z_recycle(self.z_norm(z))

            if not self.no_msa:
                z = z + self.msa_module(z, s_inputs, batch)

            s, z = self.pairformer_module(s, z, mask=mask, pair_mask=pair_mask)

        pdistogram = self.distogram_module(z)
        dict_out = {"pdistogram": pdistogram}

        if self.training and self.structure_prediction_training:
            dict_out.update(
                self.structure_module(
                    s_trunk=s,
                    z_trunk=z,
                    s_inputs=s_inputs,
                    feats=batch,
                    relative_position_encoding=relative_position_encoding,
                    multiplicity=multiplicity_diffusion_train,
                )
            )

        if (not self.training) or self.confidence_prediction:
            dict_out.update(
                self.structure_module.sample(
                    s_trunk=s,
                    z_trunk=z,
                    s_inputs=s_inputs,
                    feats=batch,
                    relative_position_encoding=relative_position_encoding,
                    num_sampling_steps=num_sampling_steps,
                    atom_mask=batch.get("atom_pad_mask", torch.ones(2, 32)),
                    multiplicity=diffusion_samples,
                    train_accumulate_token_repr=self.training,
                )
            )

        if self.confidence_prediction:
            dict_out.update(
                self.confidence_module(
                    s_inputs=s_inputs.detach(),
                    s=s.detach(),
                    z=z.detach(),
                    s_diffusion=(
                        dict_out["diff_token_repr"]
                        if self.confidence_module.use_s_diffusion
                        else None
                    ),
                    x_pred=dict_out["sample_atom_coords"].detach(),
                    feats=batch,
                    pred_distogram_logits=dict_out["pdistogram"].detach(),
                    multiplicity=diffusion_samples,
                )
            )

        if self.confidence_prediction and self.confidence_module.use_s_diffusion:
            dict_out.pop("diff_token_repr", None)

        return dict_out

def create_mock_checkpoint():
    """Create mock model checkpoint"""
    model = MockBoltzModel()
    
    # Create test model directory
    model_dir = Path.home() / ".bolzt" / "models" / "default"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Save model checkpoint with all hyperparameters
    checkpoint = {
        'epoch': 0,
        'global_step': 0,
        'pytorch-lightning_version': '2.0.0',
        'state_dict': model.state_dict(),
        'hyper_parameters': {
            'atom_s': 64,
            'atom_z': 32,
            'token_s': 128,
            'token_z': 64,
            'num_bins': 50,
            'training_args': {"batch_size": 2},
            'validation_args': {"val_check_interval": 1.0},
            'embedder_args': {
                "atom_encoder_depth": 3,
                "atom_encoder_heads": 4,
                "atoms_per_window_queries": 32,
                "atoms_per_window_keys": 128,
                "atom_feature_dim": 128,
                "no_atom_encoder": False
            },
            'msa_args': {
                "num_sequences": 10,
                "msa_s": 32,
                "msa_blocks": 2,
                "msa_dropout": 0.1,
                "z_dropout": 0.1
            },
            'pairformer_args': {
                "num_layers": 2,
                "num_blocks": 4,
                "num_heads": 4,
                "hidden_size": 32
            },
            'score_model_args': {"hidden_size": 64},
            'diffusion_process_args': {"num_steps": 100},
            'diffusion_loss_args': {"loss_type": "l2"},
            'confidence_model_args': {"hidden_size": 32},
            'confidence_prediction': True,
            'structure_prediction_training': True,
            'no_msa': False
        }
    }
    torch.save(checkpoint, model_dir / "model.ckpt")

if __name__ == "__main__":
    create_mock_checkpoint()
