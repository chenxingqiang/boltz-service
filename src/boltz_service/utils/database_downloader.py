"""Database downloader utilities"""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from tqdm import tqdm

from boltz_service.utils.database_config import BFDConfig, DatabaseConfig

# BFD database URLs
BFD_BASE_URL = "http://wwwuser.gwdg.de/~compbiol/uniclust/2018_08/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt"
BFD_FILES = {
    "ffindex": "_a3m.ffindex",
    "ffdata": "_a3m.ffdata", 
    "cs219_index": "_cs219.ffindex",
    "cs219_data": "_cs219.ffdata",
    "hhm_index": "_hhm.ffindex",
    "hhm_data": "_hhm.ffdata"
}

def calculate_md5(file_path: Path) -> str:
    """Calculate MD5 hash of a file
    
    Parameters
    ----------
    file_path : Path
        Path to file
        
    Returns
    -------
    str
        MD5 hash
    """
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

def download_file(url: str, target_path: Path, desc: str = None) -> None:
    """Download file with progress bar
    
    Parameters
    ----------
    url : str
        URL to download from
    target_path : Path
        Path to save file to
    desc : str, optional
        Description for progress bar
    """
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        with tqdm(total=total_size, unit='iB', unit_scale=True, desc=desc) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    tmp_file.write(chunk)
                    pbar.update(len(chunk))
    
    # Move temp file to target path
    shutil.move(tmp_file.name, target_path)

def download_bfd(target_dir: Path) -> Optional[BFDConfig]:
    """Download BFD database
    
    Parameters
    ----------
    target_dir : Path
        Directory to download to
        
    Returns
    -------
    BFDConfig or None
        BFD configuration if successful, None otherwise
    """
    target_dir = Path(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading BFD database to {target_dir}")
    
    try:
        for file_type, suffix in BFD_FILES.items():
            url = f"{BFD_BASE_URL}{suffix}"
            target_path = target_dir / f"bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt{suffix}"
            
            if not target_path.exists():
                print(f"Downloading {file_type}...")
                download_file(url, target_path, desc=f"Downloading {file_type}")
            else:
                print(f"File {file_type} already exists, skipping download")
                
        # Verify downloads
        bfd_config = BFDConfig.from_env()
        if bfd_config is None:
            print("Failed to verify downloaded files")
            return None
            
        print("Successfully downloaded and verified BFD database")
        return bfd_config
        
    except Exception as e:
        print(f"Error downloading BFD database: {e}")
        return None

def download_databases(target_dir: Path) -> DatabaseConfig:
    """Download all required databases
    
    Parameters
    ----------
    target_dir : Path
        Directory to download to
        
    Returns
    -------
    DatabaseConfig
        Database configuration
    """
    target_dir = Path(target_dir)
    
    # Set environment variables for database paths
    os.environ["BOLTZ_BFD_PATH"] = str(target_dir / "bfd")
    
    # Download BFD database
    bfd_config = download_bfd(target_dir / "bfd")
    
    return DatabaseConfig(
        bfd=bfd_config
    )
