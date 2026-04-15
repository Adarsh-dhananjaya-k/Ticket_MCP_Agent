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
    
    # Safely migrate existing tables by adding token tracking columns if they don't exist
    for col in ["prompt_tokens", "completion_tokens", "total_tokens"]:
        try:
            c.execute(f"ALTER TABLE chat_logs ADD COLUMN {col} INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.commit()
    conn.close()
    print("✅ Database initialized at", DB_PATH)

def log_interaction(user_email: str, role: str, message: str, tool_name: str = None, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
    """Logs a single message or tool execution to the database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO chat_logs (timestamp, user_email, role, message, tool_name, prompt_tokens, completion_tokens, total_tokens) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.utcnow().isoformat() + "Z", user_email, role, message, tool_name, prompt_tokens, completion_tokens, total_tokens)
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

def get_snow_stats():
    import requests
    from requests.auth import HTTPBasicAuth
    from dotenv import load_dotenv

    load_dotenv()
    INSTANCE = os.getenv("SNOW_INSTANCE")
    USER = os.getenv("SNOW_USER")
    PWD = os.getenv("SNOW_PASSWORD")

    if not INSTANCE:
        return {"created": 0, "on_hold": 0, "resolved": 0}

    instance_clean = INSTANCE.replace("https://", "").replace("http://", "").strip("/")
    url = f"https://{instance_clean}/api/now/stats/incident"
    params = {"sysparm_count": "true", "sysparm_group_by": "state"}

    stats = {"new": 0, "in_progress": 0, "on_hold": 0, "resolved": 0}

    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params, timeout=10)
        if res.status_code == 200:
            result = res.json().get("result", [])
            for row in result:
                fields = row.get("groupby_fields", [])
                if not fields:
                    continue
                state_val = fields[0].get("value")
                count = int(row.get("stats", {}).get("count", 0))
                if state_val == "1":
                    stats["new"] += count
                elif state_val == "2":
                    stats["in_progress"] += count
                elif state_val == "3":
                    stats["on_hold"] += count
                elif state_val in ["6", "7"]:
                    stats["resolved"] += count
    except Exception as e:
        print(f"⚠️ Error fetching SNOW stats: {e}")

    return stats

def get_snow_assignment_groups():
    """Returns incident counts grouped by assignment_group+state from ServiceNow."""
    import requests
    from requests.auth import HTTPBasicAuth
    from dotenv import load_dotenv

    load_dotenv()
    INSTANCE = os.getenv("SNOW_INSTANCE", "").replace("https://", "").replace("http://", "").strip("/")
    USER = os.getenv("SNOW_USER")
    PWD = os.getenv("SNOW_PASSWORD")

    if not INSTANCE:
        return []

    url = f"https://{INSTANCE}/api/now/stats/incident"
    params = {
        "sysparm_count": "true",
        "sysparm_group_by": "assignment_group,state",
        "sysparm_display_value": "true",
        "sysparm_limit": 500,
    }

    # state value -> label map
    STATE_LABELS = {
        "1": "New", "2": "In Progress", "3": "On Hold",
        "6": "Resolved", "7": "Closed", "8": "Canceled"
    }

    # dict: { group_name: { state_label: count } }
    groups_map = {}
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params, timeout=15)
        if res.status_code == 200:
            for row in res.json().get("result", []):
                fields = row.get("groupby_fields", [])
                if len(fields) < 2:
                    continue

                # Field 0 = assignment_group, Field 1 = state
                raw_group = fields[0].get("display_value") or fields[0].get("value") or ""
                group_name = raw_group.strip() or "(empty)"

                state_val  = fields[1].get("value", "")
                state_label = STATE_LABELS.get(state_val, f"State {state_val}")
                count = int(row.get("stats", {}).get("count", 0))

                if group_name not in groups_map:
                    groups_map[group_name] = {}
                groups_map[group_name][state_label] = groups_map[group_name].get(state_label, 0) + count

    except Exception as e:
        print(f"⚠️ Error fetching SNOW assignment groups: {e}")

    # Build sorted list: total tickets desc
    result = []
    for group_name, states in groups_map.items():
        total = sum(states.values())
        result.append({"group": group_name, "total": total, "states": states})
    result.sort(key=lambda x: x["total"], reverse=True)
    return result

def get_token_usage():
    """Returns the aggregated token usage metrics from the database."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Total overall tokens
    c.execute("SELECT SUM(prompt_tokens), SUM(completion_tokens), SUM(total_tokens) FROM chat_logs")
    overall = c.fetchone()
    
    # Today's tokens
    now_dt = datetime.utcnow()
    today_start = now_dt.strftime('%Y-%m-%d') + 'T00:00:00Z'
    c.execute("SELECT SUM(total_tokens) FROM chat_logs WHERE timestamp >= ?", (today_start,))
    today_total = c.fetchone()[0] or 0

    # 🚀 ROLLING 60S WINDOW (TPM / RPM)
    minute_ago = (now_dt - timedelta(seconds=60)).isoformat() + 'Z'
    
    # TPM: Sum of total_tokens for both 'bot' and 'bot_internal' roles
    c.execute("""
        SELECT SUM(total_tokens), COUNT(*) 
        FROM chat_logs 
        WHERE timestamp >= ? AND role IN ('bot', 'bot_internal')
    """, (minute_ago,))
    rolling = c.fetchone()
    tpm = rolling[0] or 0
    rpm = rolling[1] or 0

    conn.close()

    overall_pt = overall[0] or 0
    overall_ct = overall[1] or 0
    overall_tt = overall[2] or 0

    return {
        "overall": {
            "prompt": overall_pt,
            "completion": overall_ct,
            "total": overall_tt
        },
        "today": today_total,
        "rolling": {
            "tpm": tpm,
            "rpm": rpm
        }
    }