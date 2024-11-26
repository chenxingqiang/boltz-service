#!/bin/bash

# Create __init__.py if it doesn't exist
touch __init__.py

# Generate Python code from proto files
python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    common.proto \
    inference_service.proto \
    msa_service.proto \
    training_service.proto
