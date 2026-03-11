# import json
# import os
# import requests
# from requests.auth import HTTPBasicAuth
# from dotenv import load_dotenv

# load_dotenv()

# # --- CONFIG ---
# INSTANCE = os.getenv("SNOW_INSTANCE")
# if INSTANCE:
#     INSTANCE = INSTANCE.replace("https://", "").replace("http://", "").strip("/")
# USER = os.getenv("SNOW_USER")
# PWD = os.getenv("SNOW_PASSWORD")

# # ServiceNow States Mapping
# SN_STATE_MAP = {
#     "open": "1", "new": "1", "in progress": "2", "on hold": "3",
#     "resolved": "6", "closed": "7", "canceled": "8"
# }

# def is_configured():
#     return INSTANCE and "devXXXXX" not in INSTANCE and USER != "admin"

# def get_user_sysid(email):
#     """
#     Lookup SysID by Email.
#     """
#     if not is_configured() or not email: return None
    
#     url = f"https://{INSTANCE}/api/now/table/sys_user"
#     params = {
#         "sysparm_query": f"email={email}",
#         "sysparm_fields": "sys_id",
#         "sysparm_limit": 1
#     }
    
#     try:
#         response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
#         data = response.json().get("result", [])
#         if data:
#             return data[0]["sys_id"]
#         return None
#     except Exception as e:
#         print(f"⚠️ Error looking up user {email}: {e}")
#         return None

# def get_tickets(query_params=None):
#     if not is_configured(): return "❌ ServiceNow is NOT configured."
#     url = f"https://{INSTANCE}/api/now/table/incident"
#     params = {"sysparm_limit": 20}
#     if query_params:
#         q_strings = [f"{k}={v}" for k, v in query_params.items()]
#         params["sysparm_query"] = "^".join(q_strings)
#     try:
#         response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
#         results = response.json().get("result", [])
#         return [{"id": r["number"], "desc": r["short_description"], "status": r["state"], "priority": r["priority"]} for r in results]
#     except Exception as e:
#         return f"Fetch Error: {str(e)}"

# def get_unassigned_tickets():
#     if not is_configured(): return []
#     # state=1 (New), assigned_to is empty
#     return get_tickets({"state": "1", "assigned_to": ""})

# def create_incident(short_desc, impact="3", urgency="3"):
#     # ... (Same as before) ...
#     if not is_configured(): return "❌ Config Error"
#     url = f"https://{INSTANCE}/api/now/table/incident"
#     payload = {"short_description": short_desc, "impact": impact, "urgency": urgency, "state": "1", "assignment_group": "Software"}
#     try:
#         res = requests.post(url, auth=HTTPBasicAuth(USER, PWD), json=payload)
#         return f"Created {res.json().get('result', {}).get('number')}"
#     except Exception as e: return str(e)
# # In servicenow.py

# def update_incident(ticket_id, **kwargs):
#     """
#     Updates ticket. Looks up email to get SysID.
#     Handles mandatory fields for Resolution.
#     """
#     if not is_configured(): return "❌ Config Error"

#     url = f"https://{INSTANCE}/api/now/table/incident"
#     params = {"sysparm_query": f"number={ticket_id}"}
    
#     try:
#         # 1. Get Ticket SysID
#         res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
#         records = res.json().get("result", [])
#         if not records: return "Ticket not found"
#         sys_id = records[0]["sys_id"]

#         # 2. Map Payload
#         payload = {}
        
#         # Determine State
#         if "status" in kwargs:
#             target_state = SN_STATE_MAP.get(str(kwargs["status"]).lower(), "2")
#             payload["state"] = target_state
            
#             # --- FIX: HANDLE MANDATORY FIELDS FOR RESOLUTION ---
#             if target_state in ["6", "7"]: # 6=Resolved, 7=Closed
#                 # ServiceNow requires these fields when resolving
#                 payload["close_code"] = "Solved (Permanently)" 
#                 # Use the comments as the close notes, or a default
#                 payload["close_notes"] = kwargs.get("comments", "Resolved by AI Agent via Chat")

#         # --- ASSIGNMENT LOGIC ---
#         if "assigned_to" in kwargs:
#             email = kwargs["assigned_to"]
#             user_sys_id = get_user_sysid(email)
            
#             if user_sys_id:
#                 payload["assigned_to"] = user_sys_id
#             else:
#                 return f"❌ Error: User '{email}' not found in ServiceNow. Cannot assign."

#         # Add comments to work notes as well if provided
#         if "comments" in kwargs:
#             payload["comments"] = kwargs["comments"]
            
#         if "impact" in kwargs: payload["impact"] = kwargs["impact"]
#         if "urgency" in kwargs: payload["urgency"] = kwargs["urgency"]

#         # 3. Patch
#         update_url = f"{url}/{sys_id}"
#         response = requests.patch(update_url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        
#         # Check for HTTP errors
#         try:
#             response.raise_for_status()
#         except requests.exceptions.HTTPError as http_err:
#             # Print the actual error from ServiceNow to help debug
#             print(f"❌ ServiceNow API Error: {response.text}")
#             return f"ServiceNow rejected the update: {response.json().get('error', {}).get('message')}"
        
#         return f"Updated {ticket_id} successfully."
        
#     except Exception as e:
#         return f"Update Error: {str(e)}"

# def test_connection():
#     return "✅ Connected" if is_configured() else "❌ Not Configured"

import json
import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
INSTANCE = os.getenv("SNOW_INSTANCE")
if INSTANCE:
    INSTANCE = INSTANCE.replace("https://", "").replace("http://", "").strip("/")
USER = os.getenv("SNOW_USER")
PWD = os.getenv("SNOW_PASSWORD")

# ServiceNow States Mapping
SN_STATE_MAP = {
    "open": "1", "new": "1", "in progress": "2", "hold": "3", "on hold": "3", "pending": "3",
    "resolved": "6", "closed": "7", "canceled": "8"
}

def is_configured():
    return INSTANCE and "dev" in INSTANCE and USER

def get_sysid_by_query(table, query):
    """Helper to find a SysID based on a query."""
    if not is_configured(): return None
    url = f"https://{INSTANCE}/api/now/table/{table}"
    params = {"sysparm_query": query, "sysparm_fields": "sys_id", "sysparm_limit": 1}
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        data = res.json().get("result", [])
        return data[0]["sys_id"] if data else None
    except:
        return None

def _looks_like_sysid(value: str) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    return len(value) == 32 and value.isalnum()

def get_valid_resolution_codes():
    """
    Fetch valid Resolution Codes from sys_choice table.
    Returns the first valid value found, or a safe default.
    """
    if not is_configured(): return "Solution Provided"
    
    url = f"https://{INSTANCE}/api/now/table/sys_choice"
    # Query for choices on the 'incident' table for field 'close_code'
    params = {
        "sysparm_query": "name=incident^element=close_code^inactive=false",
        "sysparm_fields": "value,label",
        "sysparm_limit": 1
    }
    
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        choices = res.json().get("result", [])
        if choices:
            best_choice = choices[0]["value"]
            print(f"✅ Found valid Resolution Code: '{best_choice}'")
            return best_choice
    except Exception as e:
        print(f"⚠️ Could not fetch resolution codes: {e}")
    
    return "Solved (Permanently)" # Fallback

def get_user_sysid(email):
    return get_sysid_by_query("sys_user", f"email={email}")

def get_admin_sysid():
    return get_sysid_by_query("sys_user", "user_name=admin")

def get_all_groups():
    """Fetches all assignment groups from ServiceNow."""
    if not is_configured(): return []
    url = f"https://{INSTANCE}/api/now/table/sys_user_group"
    params = {"sysparm_fields": "name,sys_id,manager", "sysparm_limit": 100}
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        return res.json().get("result", [])
    except:
        return []

def get_group_members(group_sys_id):
    """Fetches all users belonging to a specific group."""
    if not is_configured() or not group_sys_id: return []
    # Join sys_user_grmember with sys_user to get email/name
    url = f"https://{INSTANCE}/api/now/table/sys_user_grmember"
    params = {
        "sysparm_query": f"group={group_sys_id}",
        "sysparm_fields": "user.name,user.email,user.manager.email,user.manager.name",
        "sysparm_display_value": "true",
        "sysparm_limit": 50
    }
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        raw_members = res.json().get("result", [])
        
        # Flatten the dot-walked fields
        members = []
        for m in raw_members:
            members.append({
                "name": m.get("user.name"),
                "email": m.get("user.email"),
                "manager_name": m.get("user.manager.name"),
                "manager_email": m.get("user.manager.email")
            })
        return members
    except:
        return []

def get_tickets(query_params=None):
    if not is_configured(): return "❌ ServiceNow is NOT configured."
    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_limit": 20, "sysparm_display_value": "true"}
    if query_params:
        q_strings = [f"{k}={v}" for k, v in query_params.items()]
        params["sysparm_query"] = "^".join(q_strings)
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        results = response.json().get("result", [])
        
        def val(field):
            if isinstance(field, dict): return field.get("display_value", "")
            return str(field) if field else ""

        processed_results = []
        for r in results:
            processed_results.append({
                "id": val(r.get("number")),
                "desc": val(r.get("short_description")),
                "status": val(r.get("state")),
                "priority": val(r.get("priority")),
                "assigned_to": val(r.get("assigned_to")),
                "assignment_group": val(r.get("assignment_group")),
                "caller": val(r.get("caller_id"))
            })
        return processed_results
    except Exception as e:
        return f"Fetch Error: {str(e)}"

def get_unassigned_tickets():
    if not is_configured(): return []
    return get_tickets({"state": "1", "assigned_to": ""})

def create_incident(short_desc, impact="3", urgency="3"):
    if not is_configured(): return "❌ Config Error"
    url = f"https://{INSTANCE}/api/now/table/incident"
    
    caller_id = get_admin_sysid()
    payload = {
        "short_description": short_desc, 
        "impact": impact, 
        "urgency": urgency, 
        "state": "1"
    }
    if caller_id: payload["caller_id"] = caller_id

    try:
        res = requests.post(url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        if res.status_code != 201: return f"Error: {res.text}"
        return f"Created {res.json().get('result', {}).get('number')}"
    except Exception as e: return str(e)

def update_incident(ticket_id, **kwargs):
    if not is_configured(): return "❌ Config Error"

    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_query": f"number={ticket_id}"}
    
    try:
        # 1. Get Ticket Data
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        records = res.json().get("result", [])
        if not records: return "Ticket not found"
        
        ticket_data = records[0]
        sys_id = ticket_data["sys_id"]
        current_caller = ticket_data.get("caller_id", "")

        # 2. Prepare Payload
        payload = {}
        
        if "status" in kwargs:
            target_state = SN_STATE_MAP.get(str(kwargs["status"]).lower())
            if not target_state:
                # Fallback check for partial matches like "progress", "resolved", etc.
                matches = [v for k,v in SN_STATE_MAP.items() if str(kwargs["status"]).lower() in k]
                if matches: target_state = matches[0]
                else: return f"❌ Error: '{kwargs['status']}' is not a valid status. Valid options are: {', '.join(SN_STATE_MAP.keys())}"
            payload["state"] = target_state
            
            # --- INTELLIGENT RESOLUTION FIX ---
            if target_state in ["6", "7"]: # Resolved/Closed
                # Auto-fetch a valid code from the system
                valid_code = get_valid_resolution_codes()
                payload["close_code"] = valid_code
                payload["close_notes"] = kwargs.get("comments", "Resolved by AI Agent")
                
                # Patch Caller if missing
                if not current_caller:
                    print("⚠️ Caller missing. Patching with 'admin'.")
                    admin_id = get_admin_sysid()
                    if admin_id: payload["caller_id"] = admin_id

        if "assigned_to" in kwargs:
            email = kwargs["assigned_to"]
            user_sys_id = get_user_sysid(email)
            if user_sys_id:
                payload["assigned_to"] = user_sys_id
            else:
                return f"❌ Error: User '{email}' not found."

        assignment_group_value = kwargs.get("assignment_group")
        if assignment_group_value is None and "assigned_to" in kwargs:
            assignment_group_value = ticket_data.get("assignment_group")

        if assignment_group_value:
            if isinstance(assignment_group_value, dict):
                assignment_group_value = assignment_group_value.get("value")
            group_sys_id = assignment_group_value
            if not _looks_like_sysid(group_sys_id):
                group_sys_id = get_sysid_by_query("sys_user_group", f"name={assignment_group_value}")
            if not group_sys_id:
                return f"❌ Error: Assignment group '{assignment_group_value}' not found."
            payload["assignment_group"] = group_sys_id

        if "comments" in kwargs:
            payload["comments"] = kwargs["comments"]

        # 3. Send Update
        update_url = f"{url}/{sys_id}"
        response = requests.patch(update_url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        
        if response.status_code != 200:
            err = response.json().get("error", {})
            print(f"❌ ServiceNow Error: {err.get('message')} | {err.get('detail')}")
            return f"ServiceNow Rejected Update: {err.get('message')}. {err.get('detail')}"
        
        return f"Updated {ticket_id} successfully."
        
    except Exception as e:
        return f"Update Error: {str(e)}"

def test_connection():
    return "✅ Connected" if is_configured() else "❌ Not Configured"
