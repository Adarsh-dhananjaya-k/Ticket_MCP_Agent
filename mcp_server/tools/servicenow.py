import json
import os
import requests
from datetime import datetime
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
INSTANCE = os.getenv("SNOW_INSTANCE")
if INSTANCE:
    INSTANCE = INSTANCE.replace("https://", "").replace("http://", "").strip("/")
USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")

# ServiceNow States Mapping (Default SN values)
# 1: New, 2: In Progress, 3: On Hold, 6: Resolved, 7: Closed, 8: Canceled
SN_STATE_MAP = {
    "open": "1",
    "new": "1",
    "in progress": "2",
    "on hold": "3",
    "resolved": "6",
    "closed": "7",
    "canceled": "8"
}

# Helper to check if real credentials are set
def is_configured():
    # Only return True if instance is NOT the placeholder
    return INSTANCE and "devXXXXX" not in INSTANCE and USER != "admin"

def create_incident(short_desc, impact="3", urgency="3"):
    """
    Creates a ticket. Uses real ServiceNow API.
    Priority is automatically calculated by ServiceNow based on Impact and Urgency.
    Impact/Urgency: 1 (High), 2 (Medium), 3 (Low)
    """
    if not is_configured():
        return "❌ ServiceNow is NOT configured in .env."

    url = f"https://{INSTANCE}/api/now/table/incident"
    payload = {
        "short_description": short_desc,
        "impact": impact,
        "urgency": urgency,
        "state": "1", # New
        "assignment_group": "Software" 
    }
    try:
        response = requests.post(url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        response.raise_for_status()
        data = response.json()
        num = data.get("result", {}).get("number", "UNKNOWN")
        prio = data.get("result", {}).get("priority", "UNKNOWN")
        return f"Created {num} with Priority {prio} (ServiceNow)"
    except Exception as e:
        return f"Error creating ServiceNow ticket: {str(e)}"

def get_tickets(query_params=None):
    """
    Access tickets from ServiceNow.
    query_params: dict for filtering (e.g., {"priority": "1"})
    """
    if not is_configured():
        return "❌ ServiceNow is NOT configured in .env."

    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_limit": 20}
    if query_params:
        # Construct encoded query if provided
        q_strings = [f"{k}={v}" for k, v in query_params.items()]
        params["sysparm_query"] = "^".join(q_strings)
        
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        response.raise_for_status()
        results = response.json().get("result", [])
        return [{"id": r["number"], "desc": r["short_description"], "status": r["state"], "priority": r["priority"]} for r in results]
    except Exception as e:
        return f"ServiceNow Fetch Error: {str(e)}"

def get_unassigned_tickets():
    """Specifically fetches tickets needing assignment."""
    if not is_configured():
        return []
        
    # state=1 is 'New'
    return get_tickets({"state": "1", "assigned_to": ""})

def update_incident(ticket_id, **kwargs):
    """
    Updates the ticket status, assignee, etc.
    Accepts: status (open, closed, in progress), assigned_to, etc.
    """
    if not is_configured():
        return "❌ ServiceNow is NOT configured in .env."

    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_query": f"number={ticket_id}"}
    try:
        # 1. Get SysID
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        records = res.json().get("result", [])
        if not records: return "Ticket not found"
        sys_id = records[0]["sys_id"]

        # 2. Map Payload
        payload = {}
        if "status" in kwargs:
            status_val = str(kwargs["status"]).lower()
            payload["state"] = SN_STATE_MAP.get(status_val, "2") # Default to In Progress if unknown
        if "assigned_to" in kwargs:
            payload["assigned_to"] = kwargs["assigned_to"]
        if "comments" in kwargs:
            payload["comments"] = kwargs["comments"]
        if "impact" in kwargs:
            payload["impact"] = kwargs["impact"]
        if "urgency" in kwargs:
            payload["urgency"] = kwargs["urgency"]

        # 3. Patch
        update_url = f"{url}/{sys_id}"
        response = requests.patch(update_url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        response.raise_for_status()
        
        return f"Updated {ticket_id} in ServiceNow"
    except requests.exceptions.HTTPError as he:
        try:
            error_detail = he.response.json().get("error", {}).get("message", "Unknown SN Error")
            return f"ServiceNow Error: {error_detail}"
        except:
            return f"ServiceNow HTTP Error: {str(he)}"
    except Exception as e:
        return f"ServiceNow Update Error: {str(e)}"

def test_connection():
    """Verifies connection to ServiceNow."""
    if not is_configured():
        return "❌ ServiceNow is NOT configured in .env."
    
    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_limit": 1}
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        if response.status_code == 200:
            return "✅ Successfully connected to ServiceNow API!"
        else:
            return f"❌ Connection failed with status {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Connection error: {str(e)}"
