import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "approval_tracker.sqlite"


def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approval_requests (
            ticket_id TEXT PRIMARY KEY,
            manager_email TEXT,
            agent_email TEXT,
            assignment_group TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    return conn


def is_pending(ticket_id: str) -> bool:
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM approval_requests WHERE ticket_id = ?", (ticket_id,)
        )
        return cur.fetchone() is not None


def mark_pending(
    ticket_id: str, manager_email: str, agent_email: str, assignment_group: Optional[str]
) -> None:
    with _get_conn() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO approval_requests
            (ticket_id, manager_email, agent_email, assignment_group)
            VALUES (?, ?, ?, ?)
            """,
            (ticket_id, manager_email, agent_email, assignment_group),
        )


def clear(ticket_id: str) -> None:
    with _get_conn() as conn:
        conn.execute("DELETE FROM approval_requests WHERE ticket_id = ?", (ticket_id,))
