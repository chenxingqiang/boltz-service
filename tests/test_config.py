"""Unit tests for :mod:`boltz_service.config.base`.

These tests exercise the pure-Python configuration layer and therefore do not
require the heavy optional dependencies (torch, grpc, ...). They act as a
lightweight safety net for refactoring work.
"""

from __future__ import annotations

from pathlib import Path

from boltz_service.config.base import BaseConfig


def test_defaults() -> None:
    """Default configuration exposes expected service values."""
    config = BaseConfig()

    assert config.service_name == "boltz"
    assert config.network.host == "0.0.0.0"  # noqa: S104
    assert config.network.port == 50051
    assert config.accelerator.type == "cpu"
    assert config.accelerator.device_ids == [0]


def test_from_env_overrides_nested_values(monkeypatch) -> None:
    """Single-token leaf attributes are overridden from BOLTZ_* env vars."""
    monkeypatch.setenv("BOLTZ_NETWORK_PORT", "60000")
    monkeypatch.setenv("BOLTZ_NETWORK_HOST", "127.0.0.1")
    monkeypatch.setenv("BOLTZ_ENVIRONMENT", "production")

    config = BaseConfig.from_env()

    assert config.network.port == 60000
    assert config.network.host == "127.0.0.1"
    assert config.environment == "production"


def test_from_env_ignores_invalid_int(monkeypatch) -> None:
    """Invalid integer env values fall back to the default."""
    monkeypatch.setenv("BOLTZ_NETWORK_PORT", "not-a-number")

    config = BaseConfig.from_env()

    # Invalid values are skipped, leaving the default in place.
    assert config.network.port == 50051


def test_from_env_ignores_unknown_keys(monkeypatch) -> None:
    """Unknown BOLTZ_* env keys are ignored without error."""
    monkeypatch.setenv("BOLTZ_DOES_NOT_EXIST", "value")

    # Should not raise, and unknown keys leave the config untouched.
    config = BaseConfig.from_env()

    assert isinstance(config, BaseConfig)


def test_validate_clean_config(tmp_path: Path) -> None:
    """A well-formed configuration produces no validation errors."""
    config = BaseConfig()
    config.cache.cache_dir = tmp_path / "cache"

    assert config.validate() == []


def test_validate_reports_invalid_port(tmp_path: Path) -> None:
    """An out-of-range port is reported by validate()."""
    config = BaseConfig()
    config.cache.cache_dir = tmp_path / "cache"
    config.network.port = 70000

    errors = config.validate()

    assert any("Invalid port number" in error for error in errors)


def test_validate_reports_missing_ssl_paths(tmp_path: Path) -> None:
    """Enabling SSL without cert/key paths is reported by validate()."""
    config = BaseConfig()
    config.cache.cache_dir = tmp_path / "cache"
    config.security.enable_ssl = True

    errors = config.validate()

    assert any("SSL enabled but" in error for error in errors)
