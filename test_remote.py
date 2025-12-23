#!/usr/bin/env python3
"""Remote server deployment and inference test."""

import pexpect
import sys

SSH_HOST = "region-46.seetacloud.com"
SSH_PORT = "19432"
SSH_USER = "root"
SSH_PASS = "RX+i0YS+8tMQ"

def run_ssh_command(command, timeout=1200):
    """Run a command via SSH."""
    ssh_cmd = f'ssh -o StrictHostKeyChecking=no -p {SSH_PORT} {SSH_USER}@{SSH_HOST}'
    
    child = pexpect.spawn(ssh_cmd, encoding='utf-8', timeout=timeout)
    child.logfile = sys.stdout
    
    try:
        i = child.expect(['password:', 'Password:', pexpect.EOF, pexpect.TIMEOUT], timeout=30)
        if i in [0, 1]:
            child.sendline(SSH_PASS)
            child.expect([r'\$', r'#', r'>>>'], timeout=30)
            child.sendline(command)
            child.expect(pexpect.EOF, timeout=timeout)
        return child.before
    except pexpect.TIMEOUT:
        print(f"\nTimeout after {timeout}s")
        return child.before
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        child.close()

def main():
    print("=" * 60)
    print("Deploying Boltz Model via Mirror")
    print("=" * 60)
    
    commands = """
echo "=== Setup environment ==="
cd /root/autodl-tmp
export BOLTZ_CACHE_DIR=/root/autodl-tmp/boltz-cache
mkdir -p $BOLTZ_CACHE_DIR
cd $BOLTZ_CACHE_DIR

echo "=== Download model via HuggingFace mirror ==="
# Use HuggingFace mirror for China
export HF_ENDPOINT=https://hf-mirror.com

if [ ! -f boltz1.ckpt ]; then
    echo "Downloading boltz1.ckpt from mirror..."
    wget -c "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/boltz1.ckpt" -O boltz1.ckpt 2>&1 | tail -5
fi

if [ ! -f ccd.pkl ]; then
    echo "Downloading ccd.pkl from mirror..."
    wget -c "https://hf-mirror.com/boltz-community/boltz-1/resolve/main/ccd.pkl" -O ccd.pkl 2>&1 | tail -3
fi

echo "=== Check downloaded files ==="
ls -lh /root/autodl-tmp/boltz-cache/

echo "=== Test model loading ==="
cd /root/autodl-tmp/boltz-service
export PYTHONPATH=/root/autodl-tmp/boltz-service/src:$PYTHONPATH
python3 << 'PYEOF'
import torch
import os

print(f"PyTorch: {torch.__version__}")
print(f"GPU: {torch.cuda.get_device_name(0)}")

model_path = "/root/autodl-tmp/boltz-cache/boltz1.ckpt"
ccd_path = "/root/autodl-tmp/boltz-cache/ccd.pkl"

if os.path.exists(model_path):
    size_gb = os.path.getsize(model_path) / (1024**3)
    print(f"Model file: {size_gb:.2f} GB")
    
    print("Loading checkpoint...")
    checkpoint = torch.load(model_path, map_location='cpu')
    print(f"Keys: {list(checkpoint.keys())}")
    
    if 'hyper_parameters' in checkpoint:
        hp = checkpoint['hyper_parameters']
        print(f"Model config: atom_s={hp.get('atom_s')}, token_s={hp.get('token_s')}")
    
    print("Checkpoint loaded successfully!")
else:
    print(f"Model not found: {model_path}")

if os.path.exists(ccd_path):
    print(f"CCD file: {os.path.getsize(ccd_path) / (1024**2):.1f} MB")
PYEOF

echo "=== Done ==="
exit
"""
    
    print("\nDownloading model...")
    run_ssh_command(commands, timeout=1200)
    
    print("\n" + "=" * 60)
    print("Download Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
