"""Shared config helpers: redaction and Pydantic validation.

Secret detection is schema-driven: each config model declares secret_fields
(clawlib.config.schema.Base); helpers use get_model_for_path + model.secret_fields
instead of hardcoded key names.
"""

from typing import Any

from clawlib.config.schema import (
    ALL_SECRET_FIELD_NAMES,
    SECRET_SECTIONS,
    ChannelsConfig,
    Config,
    ProviderConfig,
    get_model_for_path,
)


def validate_providers(raw: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    """Validate all provider configs through Pydantic, returning snake_case dicts for storage.

    Accepts both camelCase and snake_case input. Returns dict of name -> validated dict.
    """
    if not raw or not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for name, cfg in raw.items():
        if isinstance(cfg, dict):
            validated = ProviderConfig.model_validate(cfg)
            result[name] = validated.model_dump(exclude_none=True)
    return result


def validate_channels(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Validate channels config through ChannelsConfig model.

    Accepts camelCase or snake_case keys. Returns snake_case dict for storage.
    Only the channel sub-dicts that were present in the input are included, so
    that a partial update (e.g. only 'slack') does not clobber other channels.
    """
    if not raw or not isinstance(raw, dict):
        return {}
    result: dict[str, Any] = {}
    for channel_name, channel_cfg in raw.items():
        if not isinstance(channel_cfg, dict):
            result[channel_name] = channel_cfg
            continue
        # Validate through the per-channel model to normalize camelCase → snake_case.
        # Use exclude_none=True only (not exclude_defaults) so that explicit
        # enabled:False is preserved and not silently dropped.
        full_channels = ChannelsConfig.model_validate({channel_name: channel_cfg})
        channel_validated = full_channels.model_dump(exclude_none=True).get(channel_name, {})
        result[channel_name] = channel_validated
    return result


def _redact_value(key: str, value: Any, path: tuple[str, ...]) -> Any:
    model = get_model_for_path(Config, path) if path else None
    is_secret = (model and hasattr(model, "secret_fields") and key in model.secret_fields) or (
        key in ALL_SECRET_FIELD_NAMES
    )
    if is_secret:
        if isinstance(value, str) and len(value) > 4:
            return "***" + value[-4:]
        return "***"
    return redact(value, path + (key,))


def redact(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Recursively redact secret values in dicts and lists (for API responses)."""
    if isinstance(value, dict):
        return {k: _redact_value(k, v, path) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item, path) for item in value]
    return value


def _strip_redacted_dict(value: dict, path: tuple[str, ...]) -> dict:
    out = {}
    model = get_model_for_path(Config, path) if path else None
    for k, v in value.items():
        is_secret = (model and hasattr(model, "secret_fields") and k in model.secret_fields) or (
            k in ALL_SECRET_FIELD_NAMES
        )
        if is_secret and isinstance(v, str) and v.startswith("***"):
            continue
        out[k] = strip_redacted(v, path + (k,))
    return out


def strip_redacted(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Recursively drop secret keys whose values are still redacted (***…).

    Prevents a round-tripped GET→PUT from overwriting real secrets
    with their redacted placeholders.
    """
    if isinstance(value, dict):
        return _strip_redacted_dict(value, path)
    if isinstance(value, list):
        return [strip_redacted(item, path) for item in value]
    return value


def _is_redacted_or_empty(value: Any) -> bool:
    """True if value should be treated as 'no real secret' (do not overwrite existing)."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().startswith("***")
    return False


def _is_secret_at_path(path: tuple[str, ...], key: str) -> bool:
    """True if (path, key) denotes a secret field; uses schema secret_fields (with fallback)."""
    model = get_model_for_path(Config, path) if path else None
    if model and hasattr(model, "secret_fields") and key in model.secret_fields:
        return True
    return key in ALL_SECRET_FIELD_NAMES


def is_secret_field(path: tuple[str, ...], key: str) -> bool:
    """Public: True if (path, key) is a secret (schema-driven). Used by sanitize and callers."""
    return _is_secret_at_path(path, key)


def restore_secrets_from_existing(
    merged: dict[str, Any],
    existing: dict[str, Any],
    path: tuple[str, ...] = (),
) -> None:
    """In-place: for every secret in the config tree, if merged has empty/redacted, keep existing.

    Applies to channels and providers. When the client sends a PATCH with redacted
    (***) or omitted secret keys, we never overwrite stored secrets.
    """
    if not isinstance(merged, dict) or not isinstance(existing, dict):
        return
    for key in list(merged.keys()):
        merged_val = merged[key]
        existing_val = existing.get(key)
        child_path = path + (key,)
        if (
            key in SECRET_SECTIONS
            and key != "secrets"
            and isinstance(merged_val, dict)
            and isinstance(existing_val, dict)
        ):
            restore_secrets_from_existing(merged_val, existing_val, child_path)
            continue
        # Recurse into per-channel / per-provider dicts (path is ("channels",) or ("providers",))
        if (
            path in (("channels",), ("providers",))
            and isinstance(merged_val, dict)
            and isinstance(existing_val, dict)
        ):
            restore_secrets_from_existing(merged_val, existing_val, child_path)
            continue
        # Leaf: restore this key if it is a secret and merged has empty/redacted
        if _is_secret_at_path(path, key):
            if (
                _is_redacted_or_empty(merged_val)
                and existing_val is not None
                and not _is_redacted_or_empty(existing_val)
            ):
                merged[key] = existing_val
