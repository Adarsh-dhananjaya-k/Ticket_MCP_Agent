import sqlite3
import os
from datetime import datetime, timezone, timedelta

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

def _utc_now():
    return datetime.now(timezone.utc)

def _to_utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def _parse_iso(ts: str):
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None

def log_interaction(user_email: str, role: str, message: str, tool_name: str = None):
    """Logs a single message or tool execution to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_logs (timestamp, user_email, role, message, tool_name) VALUES (?, ?, ?, ?, ?)",
            (_to_utc_iso(_utc_now()), user_email, role, message, tool_name)
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
    return[dict(row) for row in rows]

def get_admin_stats():
    """
    Returns KPI metrics for the admin dashboard.
    Counts are computed for today (UTC) and the last 7 days.
    """
    now = _utc_now()
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute(
        "SELECT timestamp, user_email, role, message, tool_name FROM chat_logs WHERE timestamp >= ?",
        (_to_utc_iso(week_ago),)
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    def in_range(ts_str: str, start_dt: datetime) -> bool:
        dt = _parse_iso(ts_str)
        if not dt:
            return False
        return dt >= start_dt

    def is_create_ticket_success(row):
        if row.get("tool_name") != "create_ticket":
            return False
        msg = (row.get("message") or "").strip().lower()
        return msg.startswith("created ")

    tool_rows = [r for r in rows if r.get("role") == "tool"]
    user_rows = [r for r in rows if r.get("role") == "user"]

    tickets_today = sum(1 for r in tool_rows if is_create_ticket_success(r) and in_range(r.get("timestamp"), start_today))
    tickets_week = sum(1 for r in tool_rows if is_create_ticket_success(r))

    users_today = len({r.get("user_email") for r in user_rows if r.get("user_email") and in_range(r.get("timestamp"), start_today)})
    users_week = len({r.get("user_email") for r in user_rows if r.get("user_email")})

    tool_counts = {}
    for r in tool_rows:
        name = r.get("tool_name") or "unknown"
        tool_counts[name] = tool_counts.get(name, 0) + 1

    total_tool_calls = sum(tool_counts.values())
    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)
    top_tools_payload = []
    for name, count in top_tools[:5]:
        pct = round((count / total_tool_calls) * 100, 1) if total_tool_calls else 0
        top_tools_payload.append({
            "tool_name": name,
            "count": count,
            "pct": pct
        })

    return {
        "generated_at": _to_utc_iso(now),
        "tickets": {
            "today": tickets_today,
            "last_7_days": tickets_week
        },
        "users": {
            "today": users_today,
            "last_7_days": users_week
        },
        "top_tools": top_tools_payload,
        "tool_calls_last_7_days": total_tool_calls
    }

def get_sessions(limit: int = 1000, query: str = None):
    """
    Returns grouped sessions by user_email for the admin inbox view.
    Optional query filters logs by message/tool_name/user_email match.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM chat_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()

    if query:
        q = query.lower().strip()
        if q:
            def match(row):
                msg = (row.get("message") or "").lower()
                tool = (row.get("tool_name") or "").lower()
                email = (row.get("user_email") or "").lower()
                return q in msg or q in tool or q in email
            rows = [r for r in rows if match(r)]

    sessions = {}
    for r in rows:
        email = r.get("user_email") or "unknown"
        sessions.setdefault(email, []).append(r)

    session_list = []
    for email, logs in sessions.items():
        logs_sorted = sorted(logs, key=lambda r: r.get("timestamp") or "")
        last_activity = max(logs, key=lambda r: r.get("timestamp") or "").get("timestamp")
        session_list.append({
            "user_email": email,
            "last_activity": last_activity,
            "logs": logs_sorted
        })

    session_list.sort(key=lambda s: s.get("last_activity") or "", reverse=True)
    return session_list
