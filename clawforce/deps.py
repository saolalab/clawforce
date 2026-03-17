"""Shared FastAPI dependencies for all API modules."""

import logging
import os

from cryptography.fernet import Fernet
from fastapi import Request

from clawforce.core.acp import RunStore
from clawforce.core.database import get_database
from clawforce.core.domain.runtime import AgentRuntimeBackend
from clawforce.core.storage import StorageBackend
from clawforce.core.store import AgentStore, PlanStore, Store, UserStore
from clawforce.core.store.activity_events import ActivityEventsStore
from clawforce.core.store.agent_config import AgentConfigStore
from clawforce.core.store.agent_variables import AgentVariablesStore
from clawforce.core.store.plan_artifacts import PlanArtifactStore
from clawforce.core.store.process_logs import ProcessLogStore
from clawforce.core.ws import ConnectionManager

logger = logging.getLogger(__name__)


_fernet_warned: bool = False
_UNSET = object()
_fernet_instance: Fernet | None | object = _UNSET


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance from SECRETS_MASTER_KEY, or None in dev mode (plaintext).

    Cached after first call. Warns once at startup if key is not set.

    To generate a key:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    Then set: SECRETS_MASTER_KEY=<output>
    """
    global _fernet_instance, _fernet_warned
    if _fernet_instance is not _UNSET:
        return _fernet_instance  # type: ignore[return-value]

    key = os.environ.get("SECRETS_MASTER_KEY", "").strip()
    is_production = os.environ.get("CLAWFORCE_ENV", "development") == "production"
    if not key:
        if is_production:
            raise RuntimeError(
                "SECRETS_MASTER_KEY must be set in production to encrypt agent secrets at rest. "
                'Generate one with: python -c "from cryptography.fernet import Fernet; '
                'print(Fernet.generate_key().decode())"'
            )
        if not _fernet_warned:
            logger.warning(
                "SECRETS_MASTER_KEY is not set — agent secrets are stored as plaintext in the database. "
                "Set this env var in production to enable at-rest encryption."
            )
            _fernet_warned = True
        _fernet_instance = None
        return None
    try:
        _fernet_instance = Fernet(key.encode())
        return _fernet_instance
    except Exception as exc:
        logger.error(f"Invalid SECRETS_MASTER_KEY ({exc}) — falling back to plaintext storage")
        if is_production:
            raise RuntimeError(f"Invalid SECRETS_MASTER_KEY in production: {exc}") from exc
        _fernet_instance = None
        return None


def get_storage(request: Request) -> StorageBackend:
    return request.app.state.storage


def get_store(request: Request) -> Store:
    return Store(request.app.state.storage)


def get_agent_store(request: Request) -> AgentStore:
    return AgentStore(get_database(), request.app.state.storage)


def get_plan_store(request: Request) -> PlanStore:
    return PlanStore(get_database())


def get_plan_artifact_store(request: Request) -> PlanArtifactStore:
    return PlanArtifactStore(db=get_database(), storage=request.app.state.storage)


def get_user_store(request: Request) -> UserStore:
    return UserStore(get_database())


def get_runtime(request: Request) -> AgentRuntimeBackend:
    return request.app.state.runtime


def get_skill_registry():
    """Return the configured SkillRegistry. Callable for Depends()."""
    from clawlib.registry.factory import get_skill_registry as _get_skill

    return _get_skill()


def get_mcp_registry():
    """Return the configured MCPRegistry. Callable for Depends()."""
    from clawlib.registry.factory import get_mcp_registry as _get_mcp

    return _get_mcp()


def get_agent_config_store(_request: Request) -> AgentConfigStore:
    return AgentConfigStore(get_database(), fernet=_get_fernet())


def get_fernet() -> Fernet | None:
    """Return Fernet for encrypting agent secrets, or None in dev (plaintext)."""
    return _get_fernet()


def get_agent_variables_store(_request: Request) -> AgentVariablesStore:
    return AgentVariablesStore(get_database(), fernet=get_fernet())


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store


def get_activity_events_store(request: Request) -> ActivityEventsStore:
    return request.app.state.activity_events_store


def get_process_log_store(request: Request) -> ProcessLogStore:
    return request.app.state.process_log_store


def get_ws_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws_manager
