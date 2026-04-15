import sqlite3
import os
from datetime import datetime, timedelta

# Place the DB in the root folder alongside mcp_config.json
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "itsm_admin.db"))

def init_db():
    """Initializes the SQLite database and creates the logging table."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS chat_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            user_email TEXT,
            role TEXT,
            message TEXT,
            tool_name TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("✅ Database initialized at", DB_PATH)

def log_interaction(user_email: str, role: str, message: str, tool_name: str = None):
    """Logs a single message or tool execution to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_logs (timestamp, user_email, role, message, tool_name) VALUES (?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat() + "Z", user_email, role, message, tool_name)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"⚠️ Failed to log to DB: {e}")

def get_recent_logs(limit: int = 100):
    """Fetches the latest chat logs for the Admin Dashboard."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Returns dictionaries instead of tuples
    c = conn.cursor()
    c.execute("SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_stats():
    """Returns KPI statistics for the admin dashboard Overview tab."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    today_start = datetime.utcnow().strftime('%Y-%m-%d') + 'T00:00:00Z'
    week_ago    = (datetime.utcnow() - timedelta(days=7)).isoformat() + 'Z'

    # Tickets automated today (tool calls with ticket/incident in tool_name)
    c.execute(
        """SELECT COUNT(*) FROM chat_logs
           WHERE role = 'tool'
             AND (tool_name LIKE '%ticket%' OR tool_name LIKE '%incident%' OR tool_name LIKE '%create%')
             AND timestamp >= ?""",
        (today_start,)
    )
    tickets_today = c.fetchone()[0]

    # Tickets automated this week
    c.execute(
        """SELECT COUNT(*) FROM chat_logs
           WHERE role = 'tool'
             AND (tool_name LIKE '%ticket%' OR tool_name LIKE '%incident%' OR tool_name LIKE '%create%')
             AND timestamp >= ?""",
        (week_ago,)
    )
    tickets_week = c.fetchone()[0]

    # Unique users assisted
    c.execute(
        "SELECT COUNT(DISTINCT user_email) FROM chat_logs WHERE user_email IS NOT NULL AND user_email != ''"
    )
    unique_users = c.fetchone()[0]

    # Tool usage breakdown (top 6)
    c.execute(
        """SELECT tool_name, COUNT(*) AS cnt
           FROM chat_logs
           WHERE role = 'tool' AND tool_name IS NOT NULL AND tool_name != ''
           GROUP BY tool_name
           ORDER BY cnt DESC
           LIMIT 6"""
    )
    tool_usage = [{"tool": r[0], "count": r[1]} for r in c.fetchall()]

    conn.close()
    return {
        "tickets_today": tickets_today,
        "tickets_week":  tickets_week,
        "unique_users":  unique_users,
        "tool_usage":    tool_usage,
    }

def get_weekly_tickets():
    """Returns per-day ticket tool-call counts for the last 7 days (newest last)."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Build a list of the last 7 days (UTC)
    today = datetime.utcnow().date()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]  # Mon…Sun order

    result = []
    for d in days:
        day_start = d.strftime('%Y-%m-%d') + 'T00:00:00Z'
        day_end   = d.strftime('%Y-%m-%d') + 'T23:59:59Z'
        c.execute(
            """SELECT COUNT(*) FROM chat_logs
               WHERE role = 'tool'
                 AND (tool_name LIKE '%ticket%' OR tool_name LIKE '%incident%' OR tool_name LIKE '%create%')
                 AND timestamp >= ? AND timestamp <= ?""",
            (day_start, day_end)
        )
        count = c.fetchone()[0]
        result.append({
            "day":   d.strftime('%a'),   # e.g. "Mon"
            "date":  d.isoformat(),      # e.g. "2026-04-15"
            "count": count,
        })

    conn.close()
    return result

def get_sessions(per_user_limit: int = 500):
    """Returns chat logs grouped by user_email, sorted by most recent activity."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Get all distinct users, most recently active first
    c.execute(
        """SELECT user_email,
                  MAX(timestamp)  AS last_seen,
                  COUNT(*)        AS message_count
           FROM chat_logs
           WHERE user_email IS NOT NULL AND user_email != ''
           GROUP BY user_email
           ORDER BY last_seen DESC"""
    )
    users = [dict(r) for r in c.fetchall()]

    sessions = []
    for user in users:
        c.execute(
            "SELECT * FROM chat_logs WHERE user_email = ? ORDER BY timestamp ASC LIMIT ?",
            (user["user_email"], per_user_limit)
        )
        messages = [dict(r) for r in c.fetchall()]
        sessions.append({
            "email":         user["user_email"],
            "last_seen":     user["last_seen"],
            "message_count": user["message_count"],
            "messages":      messages,
        })

    conn.close()
    return sessions