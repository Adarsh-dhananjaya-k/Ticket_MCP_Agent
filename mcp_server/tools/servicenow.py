

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
    "open": "1", "new": "1", "in progress": "2", "on hold": "3",
    "resolved": "6", "closed": "7", "canceled": "8"
}

def is_configured():
    return INSTANCE and "dev" in INSTANCE and USER

def get_sysid_by_query(table, query):
    """Helper to find a SysID based on a query. GUARANTEES a raw string."""
    if not is_configured(): return None
    url = f"https://{INSTANCE}/api/now/table/{table}"
    
    # FORCE sysparm_display_value=false so SNOW gives us raw strings
    params = {
        "sysparm_query": query, 
        "sysparm_fields": "sys_id", 
        "sysparm_limit": 1,
        "sysparm_display_value": "false" 
    }
    
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        data = res.json().get("result",[])
        
        if data:
            val = data[0].get("sys_id")
            # If SNOW still returns a dict, extract the 'value' specifically
            if isinstance(val, dict):
                return str(val.get("value", "")).strip()
            return str(val).strip()
            
        return None
    except Exception as e:
        print(f"❌ Error in get_sysid_by_query: {e}")
        return None


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

def get_user_sysid(identifier):
    """
    Finds a user's SysID by checking if the Teams string matches 
    EITHER the ServiceNow 'User ID' (user_name) OR the 'Email' (email).
    """
    # The ^OR operator in ServiceNow tells it to search both fields!
    query = f"user_name={identifier}^ORemail={identifier}"
    return get_sysid_by_query("sys_user", query)

def get_admin_sysid():
    return get_sysid_by_query("sys_user", "user_name=admin")

def get_agent_workload(email: str) -> int:
    """Queries ServiceNow to count active incidents for a specific user."""
    if not is_configured(): return 0
    
    user_sysid = get_user_sysid(email)
    if not user_sysid: return 0
    
    # Using the Stats API to count records efficiently
    url = f"https://{INSTANCE}/api/now/stats/incident"
    params = {
        "sysparm_query": f"active=true^assigned_to={user_sysid}",
        "sysparm_count": "true"
    }
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        if res.status_code == 200:
            stats = res.json().get("result", {}).get("stats", {})
            return int(stats.get("count", 0))
        return 0
    except Exception as e:
        print(f"⚠️ Error fetching workload for {email}: {e}")
        return 0

def get_tickets(query_params=None):
    if not is_configured(): return "❌ ServiceNow is NOT configured."
    url = f"https://{INSTANCE}/api/now/table/incident"
    
    # sysparm_display_value=true ensures we get names like "Karen User" instead of 32-character sys_ids
    params = {"sysparm_limit": 20, "sysparm_display_value": "true"}
    
    if query_params:
        q_strings =[f"{k}={v}" for k, v in query_params.items()]
        params["sysparm_query"] = "^".join(q_strings)
        
    try:
        response = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        results = response.json().get("result",[])
        
        tickets_list =[]
        for r in results:
            # Safely extract assigned_to (ServiceNow sometimes returns a dict here)
            assigned = r.get("assigned_to", "Unassigned")
            if isinstance(assigned, dict): 
                assigned = assigned.get("display_value", "Unassigned")
                
            # Safely extract resolved_by
            resolved = r.get("resolved_by", "Unknown")
            if isinstance(resolved, dict): 
                resolved = resolved.get("display_value", "Unknown")
                
            tickets_list.append({
                "id": r["number"], 
                "desc": r["short_description"], 
                "status": r["state"], 
                "priority": r["priority"],
                "assigned_to": assigned,
                "resolved_by": resolved,
                "resolution_notes": r.get("close_notes", "") # Gives the AI context on HOW it was fixed
            })
            
        return tickets_list
        
    except Exception as e:
        return f"Fetch Error: {str(e)}"

def get_unassigned_tickets():
    if not is_configured(): return []
    return get_tickets({"state": "1", "assigned_to": ""})

def create_incident(short_desc, impact="3", urgency="3", suggested_engineer_email=None, assignment_group=None, caller_email=None):
    if not is_configured(): return "❌ Config Error"
    url = f"https://{INSTANCE}/api/now/table/incident"
    
    # --- Caller ID Logic ---
    final_caller_sysid = None
    if caller_email:
        found_sysid = get_user_sysid(caller_email)
        if found_sysid:
            final_caller_sysid = found_sysid
        else:
            short_desc = f"[Reported by External: {caller_email}] {short_desc}"
            final_caller_sysid = get_admin_sysid()
    else:
        final_caller_sysid = get_admin_sysid()

    # Default State to 'New' (1)
    target_state = "1"
    
    # Check if it is Critical
    is_critical = str(impact) == "1" and str(urgency) == "1"
    if is_critical:
        target_state = "3" # On Hold

    payload = {
        "short_description": short_desc, 
        "impact": impact, 
        "urgency": urgency, 
        "state": target_state
    }
    
    if final_caller_sysid: payload["caller_id"] = final_caller_sysid

    # Populate Team Assignment
    if assignment_group:
        group_sysid = get_sysid_by_query("sys_user_group", f"name={assignment_group}")
        if group_sysid:
            payload["assignment_group"] = group_sysid

    # --- 🔥 THE FIX: AUTO-ASSIGNMENT LOGIC 🔥 ---
    if suggested_engineer_email:
        eng_sysid = get_user_sysid(suggested_engineer_email)
        if eng_sysid:
            # 1. Always log the AI's suggestion for record-keeping
            payload["u_ai_suggested_engineer"] = eng_sysid
            
            # 2. If it is NOT Critical, Auto-Assign it directly!
            if not is_critical:
                payload["assigned_to"] = eng_sysid
                payload["state"] = "2"  # Automatically move it to 'In Progress'
    # ---------------------------------------------

    try:
        res = requests.post(url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        if res.status_code != 201: return f"Error: {res.text}"
        return f"Created {res.json().get('result', {}).get('number')}"
    except Exception as e: 
        return str(e)

def update_incident(ticket_id, action_by_email=None, **kwargs):
    if not is_configured(): return "❌ Config Error"

    url = f"https://{INSTANCE}/api/now/table/incident"
    params = {"sysparm_query": f"number={ticket_id}", "sysparm_display_value": "false"}
    
    try:
        # 1. Get Incident Data
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        records = res.json().get("result",[])
        if not records: return "Ticket not found"
        
        ticket_data = records[0]
        sys_id = ticket_data["sys_id"]
        requester_sysid = None

        # --- 🔒 SECURITY CHECK (DYNAMIC RBAC) 🔒 ---
        if action_by_email:
            requester_sysid = get_user_sysid(action_by_email)
            
            if not requester_sysid:
                return f"❌ Permission Denied: Your email '{action_by_email}' is not registered in ServiceNow."
            
            # A. Get Caller SysID
            caller_sysid = ticket_data.get("caller_id", "")
            if isinstance(caller_sysid, dict): caller_sysid = caller_sysid.get("value", "")
                
            # B. Get Assigned Agent SysID
            assigned_sysid = ticket_data.get("assigned_to", "")
            if isinstance(assigned_sysid, dict): assigned_sysid = assigned_sysid.get("value", "")
            
            # C. Get System Admin SysID (Master Key)
            admin_sysid = get_admin_sysid()

            # D. Get Group Manager SysID
            group_manager_sysid = None
            group_sysid = ticket_data.get("assignment_group", "")
            if isinstance(group_sysid, dict): group_sysid = group_sysid.get("value", "")
            
            if group_sysid:
                # Query the group table to find the official manager
                grp_url = f"https://{INSTANCE}/api/now/table/sys_user_group/{group_sysid}"
                grp_params = {"sysparm_fields": "manager", "sysparm_display_value": "false"}
                try:
                    grp_res = requests.get(grp_url, auth=HTTPBasicAuth(USER, PWD), params=grp_params)
                    manager_data = grp_res.json().get("result", {}).get("manager", "")
                    if isinstance(manager_data, dict):
                        group_manager_sysid = manager_data.get("value", "")
                    else:
                        group_manager_sysid = manager_data
                except Exception as e:
                    print(f"⚠️ Could not fetch group manager: {e}")

            # E. The VIP List
            authorized_users =[caller_sysid, assigned_sysid, group_manager_sysid, admin_sysid]
            # Clean up the list to remove empty values
            authorized_users =[u for u in authorized_users if u]

            # F. The Final Check
            if requester_sysid not in authorized_users:
                return f"❌ Permission Denied: You ({action_by_email}) are not authorized to modify {ticket_id}. Only the Caller, Assigned Agent, Team Manager, or System Admin can do this."
        # -------------------------------------------

        payload = {}
        
        if "status" in kwargs:
            target_state = SN_STATE_MAP.get(str(kwargs["status"]).lower(), "2")
            payload["state"] = target_state
            
            if target_state in ["6", "7"]: 
                valid_code = get_valid_resolution_codes()
                payload["close_code"] = valid_code
                payload["close_notes"] = kwargs.get("comments", "Resolved by AI Agent")
                
                # Force ServiceNow to register the ACTUAL user who resolved it
                if requester_sysid:
                    payload["resolved_by"] = requester_sysid
                
                # Ensure caller ID is populated
                caller_check = ticket_data.get("caller_id", "")
                if not caller_check:
                    admin_id = get_admin_sysid()
                    if admin_id: payload["caller_id"] = admin_id

        if "assigned_to" in kwargs:
            email = kwargs["assigned_to"]
            user_sys_id = get_user_sysid(email)
            if user_sys_id: payload["assigned_to"] = user_sys_id
            else: return f"❌ Error: User '{email}' not found."

        if "assignment_group" in kwargs:
            group_name = kwargs["assignment_group"]
            new_group_sys_id = get_sysid_by_query("sys_user_group", f"name={group_name}")
            if new_group_sys_id: 
                payload["assignment_group"] = new_group_sys_id
            else: 
                print(f"⚠️ Warning: Assignment group '{group_name}' not found in SNOW.")

        if "comments" in kwargs: payload["comments"] = kwargs["comments"]

        update_url = f"{url}/{sys_id}"
        response = requests.patch(update_url, auth=HTTPBasicAuth(USER, PWD), json=payload)
        
        if response.status_code != 200:
            err = response.json().get("error", {})
            return f"ServiceNow Rejected Update: {err.get('message')}. {err.get('detail')}"
        
        return f"Updated {ticket_id} successfully."
        
    except Exception as e:
        return f"Update Error: {str(e)}"
    
def check_approval_status(ticket_id):
    if not is_configured(): return "❌ Config Error"
    
    # 1. Get the approval status
    inc_sys_id = get_sysid_by_query("incident", f"number={ticket_id}")
    if not inc_sys_id: return "Ticket not found."
    
    url = f"https://{INSTANCE}/api/now/table/sysapproval_approver"
    params = {"sysparm_query": f"sysapproval={inc_sys_id}", "sysparm_limit": 1}
    
    approval_state = "none"
    try:
        res = requests.get(url, auth=HTTPBasicAuth(USER, PWD), params=params)
        data = res.json().get("result", [])
        if data: approval_state = data[0].get("state")
    except Exception as e:
        return f"Error: {str(e)}"

    # 2. Get the ACTUAL assigned user from the Incident table
    actual_assignee = "Unknown"
    if approval_state == 'approved':
        inc_url = f"https://{INSTANCE}/api/now/table/incident/{inc_sys_id}"
        inc_params = {"sysparm_fields": "assigned_to", "sysparm_display_value": "true"}
        try:
            inc_res = requests.get(inc_url, auth=HTTPBasicAuth(USER, PWD), params=inc_params)
            assigned_data = inc_res.json().get("result", {}).get("assigned_to")
            if isinstance(assigned_data, dict):
                actual_assignee = assigned_data.get("display_value", "Unknown")
        except Exception as e:
            pass

    # 3. Return a much smarter string to the AI
    if approval_state == 'approved':
        return f"Status: approved. The ticket is currently assigned to: {actual_assignee}."
    return f"Status: {approval_state}."

def test_connection():
    return "✅ Connected" if is_configured() else "❌ Not Configured"