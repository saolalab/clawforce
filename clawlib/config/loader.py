"""Configuration loading utilities (shared between admin and clawbot)."""

import json
from pathlib import Path
from typing import Any

import yaml

from clawlib.config.schema import Config


def deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
    replace_empty: bool = False,
) -> dict[str, Any]:
    """Recursively merge *override* into a shallow copy of *base*.

    Args:
        base: Base dict (not mutated).
        override: Override dict; values take precedence.
        replace_empty: If True, empty dicts in override replace nested dicts in base
            instead of merging (used for config hot-reload to clear sections).
    """
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            if replace_empty and not value:
                merged[key] = {}
            else:
                merged[key] = deep_merge(merged[key], value, replace_empty=replace_empty)
        else:
            merged[key] = value
    return merged


def _load_raw(path: Path) -> dict[str, Any]:
    """Load raw config dict from file. Format is inferred from path suffix."""
    with open(path, encoding="utf-8") as f:
        if path.suffix in (".yaml", ".yml"):
            return yaml.safe_load(f) or {}
        return json.load(f)


def _resolve_config_path(config_path: Path) -> Path | None:
    """Return the path to an existing config file, or None."""
    if config_path.exists():
        return config_path
    if config_path.name == "agent.json":
        parent = config_path.parent
        for suffix in (".yaml", ".yml"):
            alt = parent / f"agent{suffix}"
            if alt.exists():
                return alt
    return None


def load_config(config_path: Path) -> Config:
    """Load configuration from a config file (agent.json or agent.yaml / agent.yml).

    Returns default Config() when no file exists.
    """
    resolved = _resolve_config_path(config_path)
    if resolved is not None:
        try:
            data = _load_raw(resolved)
            return Config.model_validate(data)
        except (json.JSONDecodeError, yaml.YAMLError, ValueError) as e:
            print(f"Warning: Failed to load config from {resolved}: {e}")
            print("Using default configuration.")

    return Config()


def save_config(data: dict[str, Any] | Config, config_path: Path) -> None:
    """Write a config dict to disk. Format is inferred from path suffix."""
    if isinstance(data, Config):
        data = data.model_dump()
    resolved = _resolve_config_path(config_path) or config_path
    if not resolved.exists() and config_path.name == "agent.json":
        resolved = config_path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with open(resolved, "w", encoding="utf-8") as f:
        if resolved.suffix in (".yaml", ".yml"):
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        else:
            json.dump(data, f, indent=2)
