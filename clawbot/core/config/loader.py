"""Configuration loading utilities.

Re-exports deep_merge and save_config from clawlib. Overrides load_config to
return clawbot.core.config.schema.Config (the subclass with provider matching).
"""

import json
from pathlib import Path

import yaml

from clawbot.core.config.schema import Config
from clawlib.config.loader import (
    _load_raw,
    _resolve_config_path,
    deep_merge,
    save_config,
)

__all__ = ["Config", "deep_merge", "load_config", "save_config"]


def load_config(config_path: Path) -> Config:
    """Load configuration, returning the clawbot Config (with provider matching)."""
    resolved = _resolve_config_path(config_path)
    if resolved is not None:
        try:
            data = _load_raw(resolved)
            return Config.model_validate(data)
        except (json.JSONDecodeError, yaml.YAMLError, ValueError) as e:
            print(f"Warning: Failed to load config from {resolved}: {e}")
            print("Using default configuration.")
    return Config()
