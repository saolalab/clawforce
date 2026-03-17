"""Secret key names, redaction helpers, and validation for API.

Re-exports from clawlib.config.helpers and adds admin-specific helpers.
"""

from clawlib.config.helpers import redact
from clawlib.config.schema import Config


def global_config_redacted() -> dict:
    """Return default Config with secrets redacted (for API)."""
    return redact(Config().model_dump(by_alias=False))
