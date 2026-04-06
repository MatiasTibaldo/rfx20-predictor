"""
config — Project configuration.

Exposes the ``settings`` singleton (a Pydantic BaseSettings instance) that
holds all configurable values for the pipeline: paths, split ratios,
prediction horizons, active feature groups, and log level.

Usage:
    from config import settings
    print(settings.DATA_DIR)
"""

from .settings import Settings, settings

__all__ = ["Settings", "settings"]
