"""Persistence layer: agents, users, plans (SQLite)."""

from clawforce.core.database import Database, get_database
from clawforce.core.storage import StorageBackend, get_storage_backend
from clawforce.core.store.agents import AgentStore
from clawforce.core.store.base import BaseRepository
from clawforce.core.store.plans import PlanStore
from clawforce.core.store.users import UserStore


class Store:
    """Facade composing AgentStore, UserStore, and PlanStore.

    Uses a single SQLite Database and optional StorageBackend (for agent workspace).
    """

    def __init__(self, storage: StorageBackend | None = None) -> None:
        self._storage = storage or get_storage_backend()
        db = get_database()
        self.agents = AgentStore(db, self._storage)
        self.users = UserStore(db)
        self.plans = PlanStore(db)


__all__ = [
    "AgentStore",
    "BaseRepository",
    "Database",
    "PlanStore",
    "Store",
    "UserStore",
    "get_database",
]
