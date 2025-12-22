from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="boltz-service",
    version="0.1.0",
    author="Xingqiang Chen",
    author_email="chen.xingqiang@iechor.com",
    description="A high-performance protein structure prediction microservice",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/chenxingqiang/boltz-service",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Deep learning
        "torch>=2.2",
        "pytorch-lightning==2.4.0",
        
        # gRPC and networking
        "grpcio>=1.54.2",
        "grpcio-tools>=1.54.2",
        "grpcio-health-checking>=1.54.2",
        "grpcio-reflection>=1.54.2",
        "protobuf>=4.23.2",
        
        # Scientific computing
        "numpy==1.26.3",
        "scipy==1.13.1",
        "pandas==2.2.3",
        
        # Bio-informatics
        "biopython==1.84",
        "rdkit>=2024.3.2",
        
        # ML utilities
        "hydra-core==1.3.2",
        "dm-tree==0.1.8",
        "einops==0.8.0",
        "einx==0.3.0",
        "fairscale==0.4.13",
        "mashumaro==3.14",
        "modelcif==1.2",
        "wandb==0.18.7",
        
        # Utilities
        "click==8.1.7",
        "pyyaml==6.0.2",
        "requests==2.32.3",
        "types-requests",
        "psutil>=5.9.0",
        "redis>=5.0.0",
        
        # Cloud and deployment
        "boto3>=1.26.0",
        "kubernetes>=26.1.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "pytest-asyncio>=0.16.0",
            "black>=22.0",
            "isort>=5.0",
            "flake8>=3.9",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "boltz-service=boltz.main:cli",
        ],
    },
    include_package_data=True,
    package_data={
        "boltz": ["py.typed"],
    },
)
