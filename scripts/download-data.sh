#!/bin/bash

# Exit on error
set -e

# Create data directories
mkdir -p /data/bfd
mkdir -p /data/models
mkdir -p /data/cache

# Download BFD database
echo "Downloading BFD database..."
wget -P /data/bfd https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz
tar -xzf /data/bfd/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz -C /data/bfd/
rm /data/bfd/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz

# Download Boltz model files
echo "Downloading Boltz model files..."
wget -P /data/models https://huggingface.co/boltz-community/boltz-1/resolve/main/ccd.pkl
wget -P /data/models https://huggingface.co/boltz-community/boltz-1/resolve/main/boltz1.ckpt

# Download UniRef90 database (if needed)
echo "Downloading UniRef90 database..."
wget -P /data/uniref https://ftp.uniprot.org/pub/databases/uniprot/uniref/uniref90/uniref90.fasta.gz
gunzip /data/uniref/uniref90.fasta.gz

# Set permissions
chmod -R 755 /data

# Create cache directory with write permissions
chmod 777 /data/cache

echo "Data download completed!"
