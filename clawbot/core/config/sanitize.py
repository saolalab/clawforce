"""Sanitize config for agent: replace secret values with placeholder."""

from clawbot.core.config.schema import Config
from clawlib.config.helpers import is_secret_field

_SECRET_PLACEHOLDER = "***"


def _sanitize_dict(d: dict, path: tuple[str, ...] = ()) -> dict:
    out = {}
    for k, v in d.items():
        child_path = path + (k,)
        if (
            is_secret_field(path, k)
            and isinstance(v, str)
            and v
            and not v.startswith(_SECRET_PLACEHOLDER)
        ):
            out[k] = _SECRET_PLACEHOLDER
        elif child_path == ("secrets", "env") and isinstance(v, dict):
            out[k] = {ek: _SECRET_PLACEHOLDER for ek in v} if v else {}
        elif isinstance(v, dict) and not (isinstance(v, type) or hasattr(v, "model_dump")):
            out[k] = _sanitize_dict(v, child_path)
        else:
            out[k] = v
    return out


def sanitize_config_for_agent(config: Config) -> Config:
    """Return a Config copy with all secret values replaced by '***'."""
    raw = config.model_dump(by_alias=False)
    sanitized = _sanitize_dict(raw, ())
    return Config.model_validate(sanitized)
