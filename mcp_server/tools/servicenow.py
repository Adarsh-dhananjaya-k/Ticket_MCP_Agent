import json
import os
import random
from datetime import datetime

DB_FILE = "servicenow_mock_db.json"

def _load_db():
    if not os.path.exists(DB_FILE): return []
    with open(DB_FILE, "r") as f: return json.load(f)

def _save_db(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=2)

def create_incident(short_desc, priority):
    """Called by Chat Agent"""
    tickets = _load_db()
    tid = f"INC{random.randint(1000,9999)}"
    tickets.append({
        "id": tid, 
        "desc": short_desc, 
        "priority": priority, 
        "status": "New", 
        "assigned_to": "Unassigned",
        "created_at": datetime.now().isoformat()
    })
    _save_db(tickets)
    return f"Created {tid}"

def get_unassigned_tickets():
    """Called by Worker Agent"""
    tickets = _load_db()
    return [t for t in tickets if t["status"] == "New"]

def update_incident(ticket_id, **kwargs):
    """Called by Worker Agent to Assign or Close"""
    tickets = _load_db()
    for t in tickets:
        if t["id"] == ticket_id:
            t.update(kwargs)
            _save_db(tickets)
            return f"Updated {ticket_id} with {kwargs}"
    return "Ticket not found"