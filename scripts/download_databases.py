#!/usr/bin/env python3
"""Download required databases for Boltz service"""

import argparse
import os
from pathlib import Path

from boltz_service.utils.database_downloader import download_databases

def main():
    parser = argparse.ArgumentParser(description="Download required databases for Boltz service")
    parser.add_argument(
        "--target-dir",
        type=str,
        default=os.path.expanduser("~/.boltz/databases"),
        help="Directory to download databases to (default: ~/.boltz/databases)"
    )
    
    args = parser.parse_args()
    target_dir = Path(args.target_dir)
    
    print(f"Downloading databases to {target_dir}")
    config = download_databases(target_dir)
    
    if config.bfd:
        print("\nBFD database downloaded successfully!")
        print(f"BFD database path: {config.bfd.db_path}")
        print("\nTo use the local BFD database, set the following environment variable:")
        print(f"export BOLTZ_BFD_PATH={config.bfd.db_path}")
    else:
        print("\nFailed to download BFD database")
        
if __name__ == "__main__":
    main()
