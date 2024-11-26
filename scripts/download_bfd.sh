#!/bin/bash

# Downloads BFD database using aria2c.
set -e

if [[ $# -eq 0 ]]; then
  echo "Error: download directory must be provided as an input argument."
  exit 1
fi

DOWNLOAD_DIR="$1"
ROOT_DIR="${DOWNLOAD_DIR}/bfd"
SOURCE_URL="https://bfd.mmseqs.com/bfd_metaclust_clu_complete_id30_c90_final_seq.sorted_opt.tar.gz"
BASENAME=$(basename "${SOURCE_URL}")

# Create download directory
mkdir -p "${ROOT_DIR}"

echo "Downloading BFD database to ${ROOT_DIR}..."
echo "This may take a while as the database is several hundred GB in size."

# Download using aria2c
if ! command -v aria2c &> /dev/null; then
    echo "Error: aria2c is not installed. Please install it first:"
    echo "  brew install aria2"
    exit 1
fi

aria2c "${SOURCE_URL}" --dir="${ROOT_DIR}"

echo "Extracting database files..."
tar -xvf "${ROOT_DIR}/${BASENAME}" -C "${ROOT_DIR}"

echo "Cleaning up..."
rm "${ROOT_DIR}/${BASENAME}"

echo "Done! BFD database has been downloaded to ${ROOT_DIR}"
echo
echo "To use the local BFD database, set the following environment variable:"
echo "export BOLTZ_BFD_PATH=${ROOT_DIR}"
