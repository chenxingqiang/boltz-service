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
        "torch>=2.2",
        "numpy==1.26.3",
        "hydra-core==1.3.2",
        "pytorch-lightning==2.4.0",
        "rdkit>=2024.3.2",
        "dm-tree==0.1.8",
        "requests==2.32.3",
        "pandas==2.2.3",
        "types-requests",
        "einops==0.8.0",
        "einx==0.3.0",
        "fairscale==0.4.13",
        "mashumaro==3.14",
        "modelcif==1.2",
        "wandb==0.18.7",
        "click==8.1.7",
        "pyyaml==6.0.2",
        "biopython==1.84",
        "scipy==1.13.1",
        "grpcio>=1.50.0",
        "grpcio-tools>=1.50.0",
        "grpcio-health-checking>=1.50.0",
        "grpcio-reflection>=1.50.0",
        "protobuf>=3.19.0",
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
