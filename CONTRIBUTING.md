# Contributing to Boltz Service

Thank you for your interest in contributing to Boltz Service! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Review Process](#review-process)

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Please:

- Be respectful and considerate in all interactions
- Welcome newcomers and help them get started
- Focus on constructive feedback
- Accept responsibility for mistakes and learn from them

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/boltz-service.git
   cd boltz-service
   ```
3. **Add the upstream remote**:
   ```bash
   git remote add upstream https://github.com/chenxingqiang/boltz-service.git
   ```

## Development Setup

### Prerequisites

- Python 3.9 or higher
- CUDA-compatible GPU (recommended for development)
- Docker (for containerized testing)
- Redis (for MSA caching)

### Installation

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Set up pre-commit hooks:
   ```bash
   pip install pre-commit
   pre-commit install
   ```

4. Generate proto files:
   ```bash
   cd src/boltz_service/protos
   ./generate_protos.sh
   ```

### Environment Variables

Create a `.env` file in the project root:

```bash
BOLTZ_CACHE_DIR=/path/to/cache
BOLTZ_MODEL_DIR=/path/to/models
BOLTZ_BFD_PATH=/path/to/bfd
REDIS_HOST=localhost
REDIS_PORT=6379
```

## Making Changes

### Branch Naming

Use descriptive branch names:

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring
- `test/description` - Test additions or changes

### Commit Messages

Follow conventional commit format:

```
type(scope): description

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(inference): add batch prediction support
fix(msa): handle empty sequence input
docs(api): update endpoint documentation
```

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guide
- Use [NumPy-style docstrings](https://numpydoc.readthedocs.io/en/latest/format.html)
- Maximum line length: 88 characters (Black default)
- Use type hints for all function signatures

### Code Formatting

We use the following tools:

- **Ruff**: Linting and formatting
- **MyPy**: Static type checking

Run formatters before committing:
```bash
ruff check --fix src/
ruff format src/
mypy src/
```

### Documentation

- All public functions, classes, and modules must have docstrings
- Use NumPy-style docstrings:
  ```python
  def predict_structure(sequence: str, model_version: str = "latest") -> dict:
      """Predict protein structure from sequence.
      
      Parameters
      ----------
      sequence : str
          Amino acid sequence in single-letter code
      model_version : str, optional
          Model version to use, by default "latest"
          
      Returns
      -------
      dict
          Prediction results containing coordinates and confidence scores
          
      Raises
      ------
      ValueError
          If sequence contains invalid characters
      """
  ```

### File Organization

```
src/boltz_service/
├── config/          # Configuration management
├── data/            # Data processing modules
├── model/           # Model architecture
├── monitoring/      # Metrics and tracing
├── protos/          # gRPC protocol definitions
├── services/        # Service implementations
└── utils/           # Utility functions
```

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=boltz_service --cov-report=html

# Run specific test file
pytest tests/test_server.py

# Run tests matching a pattern
pytest tests/ -k "inference"
```

### Writing Tests

- Place tests in the `tests/` directory
- Mirror the source code structure
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`
- Include both positive and negative test cases

Example:
```python
import pytest
from boltz_service.services.inference import InferenceService

class TestInferenceService:
    def test_predict_structure_valid_sequence_returns_coordinates(self):
        """Test that valid sequence returns predicted coordinates."""
        service = InferenceService(config)
        result = service.predict("MVKVGVNG")
        assert "coordinates" in result
        assert result["coordinates"].shape[-1] == 3
    
    def test_predict_structure_empty_sequence_raises_error(self):
        """Test that empty sequence raises ValueError."""
        service = InferenceService(config)
        with pytest.raises(ValueError):
            service.predict("")
```

### Test Categories

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test service interactions
- **End-to-end tests**: Test complete workflows

## Submitting Changes

### Pull Request Process

1. **Update your fork**:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature
   ```

3. **Make your changes** and commit them

4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature
   ```

5. **Create a Pull Request** on GitHub

### Pull Request Checklist

Before submitting, ensure:

- [ ] Code follows the style guidelines
- [ ] All tests pass locally
- [ ] New code has appropriate tests
- [ ] Documentation is updated
- [ ] Commit messages follow conventions
- [ ] No merge conflicts with main branch

### PR Description Template

```markdown
## Summary
Brief description of changes

## Changes
- Change 1
- Change 2

## Testing
How were these changes tested?

## Related Issues
Fixes #123
```

## Review Process

### What to Expect

1. **Automated checks**: CI will run tests and linting
2. **Code review**: Maintainers will review your changes
3. **Feedback**: You may receive requests for changes
4. **Approval**: Once approved, changes will be merged

### Responding to Feedback

- Address all review comments
- Push additional commits to the same branch
- Request re-review when ready

### Merge Policy

- PRs require at least one approval
- All CI checks must pass
- Squash merging is preferred for clean history

## Questions?

If you have questions, please:

1. Check existing [issues](https://github.com/chenxingqiang/boltz-service/issues)
2. Search closed PRs for similar topics
3. Open a new issue with your question

Thank you for contributing to Boltz Service!
