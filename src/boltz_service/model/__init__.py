"""Boltz model package."""

__all__ = ["BoltzModel"]


def __getattr__(name: str):
    if name == "BoltzModel":
        from boltz_service.model.model import BoltzModel

        return BoltzModel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
