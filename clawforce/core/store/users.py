"""User CRUD operations backed by SQLite."""

from clawforce.core.database import Database
from clawforce.core.domain.agent import UserDef
from clawforce.core.store.base import BaseRepository


class UserStore(BaseRepository[UserDef]):
    """CRUD for users persisted in SQLite."""

    table_name = "users"
    model_class = UserDef

    def __init__(self, db: Database) -> None:
        super().__init__(db)

    def list_users(self) -> list[UserDef]:
        return self.list_all()

    def get_user_by_id(self, user_id: str) -> UserDef | None:
        return self.get_by_id(user_id)

    def get_user_by_username(self, username: str) -> UserDef | None:
        with self._db.connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            return self._row_to_model(row) if row else None

    def create_user(self, username: str, password_hash: str, role: str = "admin") -> UserDef:
        if self.get_user_by_username(username) is not None:
            raise ValueError(f"User already exists: {username}")
        user = UserDef(username=username, password_hash=password_hash, role=role)
        self._insert_row(user.model_dump(by_alias=False))
        return user

    def update_user(
        self,
        user_id: str,
        password_hash: str | None = None,
        role: str | None = None,
    ) -> UserDef | None:
        user = self.get_by_id(user_id)
        if not user:
            return None
        kwargs: dict = {}
        if password_hash is not None:
            kwargs["password_hash"] = password_hash
        if role is not None:
            kwargs["role"] = role
        if kwargs:
            self._update(user_id, **kwargs)
            if "password_hash" in kwargs:
                user.password_hash = kwargs["password_hash"]
            if "role" in kwargs:
                user.role = kwargs["role"]
        return user
