#!/bin/bash

# Script to download and prepare BFD database in Docker volume

set -e

# Get the volume path
VOLUME_NAME="msa_bfd_data"
VOLUME_PATH=$(docker volume inspect ${VOLUME_NAME} -f '{{ .Mountpoint }}')

if [ -z "$VOLUME_PATH" ]; then
    echo "Error: Could not find Docker volume ${VOLUME_NAME}"
    echo "Please make sure you've created the volume by running:"
    echo "docker-compose -f docker/msa/docker-compose.yml up -d"
    exit 1
fi

# Create temporary container to download BFD
echo "Creating temporary container to download BFD database..."
docker run --rm \
    -v ${VOLUME_NAME}:/data/bfd \
    -v $(pwd)/scripts:/scripts \
    --name bfd_downloader \
    python:3.11-slim \
    bash -c "apt-get update && \
             apt-get install -y aria2 && \
             /scripts/download_bfd.sh /data"

echo "BFD database has been downloaded to Docker volume ${VOLUME_NAME}"
echo "You can now start the MSA service with:"
echo "docker-compose -f docker/msa/docker-compose.yml up -d"
