"""Activity events store: append-only audit log in SQLite."""

from datetime import datetime, timezone

from clawforce.core.database import Database
from clawlib.activity import ActivityEvent


class ActivityEventsStore:
    """Persist and query activity events for audit and multi-worker support."""

    def __init__(self, db: Database) -> None:
        self._db = db

    def insert(self, event: ActivityEvent) -> bool:
        """Append one activity event. Uses INSERT OR IGNORE when event_id present (dedupe on reconnect).
        Returns True if the event was inserted, False if it was ignored (duplicate)."""
        with self._db.connection() as conn:
            created_at = datetime.now(timezone.utc).isoformat()
            ts = event.timestamp or created_at
            if event.event_id:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO activity_events (
                        agent_id, event_type, channel, content, plan_id, timestamp,
                        tool_name, result_status, duration_ms, event_id, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.agent_id,
                        event.event_type,
                        event.channel or "",
                        event.content or "",
                        event.plan_id or "",
                        ts,
                        event.tool_name,
                        event.result_status,
                        event.duration_ms,
                        event.event_id,
                        created_at,
                    ),
                )
                if cur.rowcount == 0:
                    return False
            else:
                conn.execute(
                    """INSERT INTO activity_events (
                        agent_id, event_type, channel, content, plan_id, timestamp,
                        tool_name, result_status, duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        event.agent_id,
                        event.event_type,
                        event.channel or "",
                        event.content or "",
                        event.plan_id or "",
                        ts,
                        event.tool_name,
                        event.result_status,
                        event.duration_ms,
                        created_at,
                    ),
                )
            return True

    def get_recent_for_plan(
        self,
        plan_id: str,
        agent_ids: list[str],
        limit: int = 200,
        after_id: int | None = None,
    ) -> list[dict]:
        """Return recent events for a plan, spanning all assigned agent IDs.

        Only events whose plan_id exactly matches are returned, so activity from
        the same agents on other plans is never mixed in.
        """
        if not agent_ids:
            return []
        placeholders = ",".join("?" * len(agent_ids))
        with self._db.connection() as conn:
            if after_id is not None:
                rows = conn.execute(
                    f"""SELECT id, agent_id, event_type, channel, content, plan_id,
                              timestamp, tool_name, result_status, duration_ms, event_id
                       FROM activity_events
                       WHERE agent_id IN ({placeholders})
                         AND id > ?
                         AND plan_id = ?
                       ORDER BY id ASC
                       LIMIT ?""",
                    (*agent_ids, after_id, plan_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    f"""SELECT id, agent_id, event_type, channel, content, plan_id,
                              timestamp, tool_name, result_status, duration_ms, event_id
                       FROM activity_events
                       WHERE agent_id IN ({placeholders})
                         AND plan_id = ?
                       ORDER BY id DESC
                       LIMIT ?""",
                    (*agent_ids, plan_id, limit),
                ).fetchall()
                rows = list(reversed(rows))
            return [_row_to_event(r) for r in rows]

    def get_recent(
        self,
        agent_id: str,
        limit: int = 100,
        after_id: int | None = None,
    ) -> list[dict]:
        """Return recent events for an agent, optionally after a given id (for polling)."""
        with self._db.connection() as conn:
            if after_id is not None:
                rows = conn.execute(
                    """SELECT id, agent_id, event_type, channel, content, plan_id,
                              timestamp, tool_name, result_status, duration_ms, event_id
                       FROM activity_events
                       WHERE agent_id = ? AND id > ?
                       ORDER BY id ASC
                       LIMIT ?""",
                    (agent_id, after_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT id, agent_id, event_type, channel, content, plan_id,
                              timestamp, tool_name, result_status, duration_ms, event_id
                       FROM activity_events
                       WHERE agent_id = ?
                       ORDER BY id DESC
                       LIMIT ?""",
                    (agent_id, limit),
                ).fetchall()
                rows = list(reversed(rows))  # oldest first for display
            return [_row_to_event(r) for r in rows]


def _row_to_event(row) -> dict:
    """Convert DB row to event dict matching ActivityEvent / logs API format."""
    out = {
        "id": row["id"],
        "agent_id": row["agent_id"],
        "event_type": row["event_type"],
        "channel": row["channel"] or "",
        "content": row["content"] or "",
        "plan_id": row["plan_id"] or "",
        "timestamp": row["timestamp"] or "",
        "tool_name": row["tool_name"],
        "result_status": row["result_status"],
        "duration_ms": row["duration_ms"],
    }
    if "event_id" in row.keys() and row["event_id"]:
        out["event_id"] = row["event_id"]
    return out
