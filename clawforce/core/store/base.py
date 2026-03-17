"""Base repository for SQLite-backed CRUD with Pydantic models."""

import sqlite3
from typing import Generic, TypeVar

from pydantic import BaseModel

from clawforce.core.database import Database

T = TypeVar("T", bound=BaseModel)


class BaseRepository(Generic[T]):
    """Generic repository with get_by_id, list_all, delete, _insert, _update."""

    table_name: str
    model_class: type[T]

    def __init__(self, db: Database) -> None:
        self._db = db

    def get_by_id(self, id: str) -> T | None:
        with self._db.connection() as conn:
            row = conn.execute(f"SELECT * FROM {self.table_name} WHERE id = ?", (id,)).fetchone()
            return self._row_to_model(row) if row else None

    def list_all(self) -> list[T]:
        with self._db.connection() as conn:
            rows = conn.execute(f"SELECT * FROM {self.table_name}").fetchall()
            return [self._row_to_model(r) for r in rows]

    def delete(self, id: str) -> bool:
        with self._db.connection() as conn:
            cursor = conn.execute(f"DELETE FROM {self.table_name} WHERE id = ?", (id,))
            return cursor.rowcount > 0

    def _row_to_model(self, row: sqlite3.Row) -> T:
        d = dict(row)
        return self.model_class.model_validate(d)

    def _insert(self, model: T) -> None:
        self._insert_row(model.model_dump(by_alias=False))

    def _insert_row(self, row: dict) -> None:
        """Insert a row dict; keys must match table columns (extra keys are ignored)."""
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols)
        with self._db.connection() as conn:
            conn.execute(
                f"INSERT INTO {self.table_name} ({', '.join(cols)}) VALUES ({placeholders})",
                [row[k] for k in cols],
            )

    def _update(self, id: str, **kwargs: object) -> bool:
        if not kwargs:
            return True
        cols = list(kwargs.keys())
        set_clause = ", ".join(f"{c} = ?" for c in cols)
        values = [kwargs[c] for c in cols]
        with self._db.connection() as conn:
            cursor = conn.execute(
                f"UPDATE {self.table_name} SET {set_clause} WHERE id = ?",
                values + [id],
            )
            return cursor.rowcount > 0
