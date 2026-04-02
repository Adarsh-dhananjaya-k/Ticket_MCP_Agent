import sqlite3
import os
from datetime import datetime

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
    return[dict(row) for row in rows]