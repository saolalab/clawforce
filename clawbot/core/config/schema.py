"""Configuration schema with provider matching.

Re-exports the shared Config from clawlib/ and adds provider-matching methods
that depend on clawbot.providers.registry (not shared with clawforce).
"""

import os

from clawbot.providers.registry import PROVIDERS, find_by_name
from clawlib.config.schema import *  # noqa: F401,F403
from clawlib.config.schema import Config as _BaseConfig
from clawlib.config.schema import ProviderConfig


class Config(_BaseConfig):
    """Root configuration with provider matching."""

    def model_post_init(self, __context: object) -> None:
        """Populate provider api_keys from environment variables if not set."""
        super().model_post_init(__context)
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and not p.api_key and spec.env_key:
                env_val = os.environ.get(spec.env_key)
                if env_val:
                    object.__setattr__(p, "api_key", env_val)

    def _match_provider(
        self, model: str | None = None
    ) -> tuple["ProviderConfig | None", str | None]:
        """Match provider config and its registry name. Returns (config, spec_name)."""
        model_lower = (model or self.agents.defaults.model).lower()

        # Explicit routing by "<provider>/..." prefix — deterministic and works
        # for providers with no keywords (e.g. "custom/my-model").
        if "/" in model_lower:
            prefix = model_lower.split("/", 1)[0]
            spec = find_by_name(prefix)
            if spec:
                p = getattr(self.providers, spec.name, None)
                if p is not None:
                    return p, spec.name

        # First pass: match by keyword in model name + has API key
        for spec in PROVIDERS:
            p = getattr(self.providers, spec.name, None)
            if p and any(kw in model_lower for kw in spec.keywords):
                if spec.is_oauth or p.api_key:
                    return p, spec.name

        # Second pass: fallback to first provider with API key
        for spec in PROVIDERS:
            if spec.is_oauth:
                continue
            p = getattr(self.providers, spec.name, None)
            if p and p.api_key:
                return p, spec.name
        return None, None

    def get_provider(self, model: str | None = None) -> ProviderConfig | None:
        p, _ = self._match_provider(model)
        return p

    def get_provider_name(self, model: str | None = None) -> str | None:
        _, name = self._match_provider(model)
        return name

    def get_api_key(self, model: str | None = None) -> str | None:
        p = self.get_provider(model)
        return p.api_key if p else None

    def get_api_base(self, model: str | None = None) -> str | None:
        p, name = self._match_provider(model)
        if p and p.api_base:
            return p.api_base
        if name:
            spec = find_by_name(name)
            if spec and spec.is_gateway and spec.default_api_base:
                return spec.default_api_base
        return None
