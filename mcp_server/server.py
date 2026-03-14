import json # <--- Make sure json is imported
import random
from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import create_incident, get_unassigned_tickets, update_incident, test_connection, get_tickets
from mcp_server.tools.servicenow import  check_approval_status

mcp = FastMCP("ITSM-System")

@mcp.tool()
def connection_test() -> str:
    return test_connection()

@mcp.tool()
def list_tickets(priority: str = None, state: str = None, ticket_id: str = None) -> str:
    query = {}
    if ticket_id: query["number"] = ticket_id
    if priority: query["priority"] = priority
    if state: query["state"] = state
    return json.dumps(get_tickets(query))

@mcp.tool()
def lookup_sla_policy(description: str) -> str:
    return lookup_sla(description)

@mcp.tool()
def create_ticket(description: str, impact: str = "3", urgency: str = "3") -> str:
    return create_incident(description, impact=impact, urgency=urgency)

@mcp.tool()
def fetch_new_work() -> str:
    # Ensure this returns a JSON string
    return json.dumps(get_unassigned_tickets())

# In server.py

@mcp.tool()
def update_ticket(ticket_id: str, status: str = None, assigned_to: str = None, comments: str = None) -> str:
    """
    Update ticket details.
    
    IMPORTANT: If status is 'resolved', you MUST provide a 'comments' argument 
    explaining the resolution (e.g., "Reset password", "Fixed network config").
    """
    kwargs = {k: v for k, v in locals().items() if v is not None and k != "ticket_id"}
    return update_incident(ticket_id, **kwargs)

@mcp.tool()
def find_assignee(description: str) -> str:
    """
    Returns JSON string: {agent_name, agent_email, manager_name, manager_email, ...}
    """
    # --- FIX IS HERE: Convert Dict to JSON String ---
    result_dict = find_best_assignee(description)
    return json.dumps(result_dict)

@mcp.tool()
def assign_ticket(ticket_id: str, email: str, team: str = None) -> str:
    # Now it accepts team!
    return update_incident(ticket_id, assigned_to=email, assignment_group=team, status="Assigned")

@mcp.tool()
def request_manager_approval(agent_email: str, manager_email: str, team: str, ticket_id: str, reason: str) -> str:
    """Assigns ticket, puts it On Hold, and creates Approval Record via Custom API."""
    print(f"\n⚙️[APPROVAL] Assigning {ticket_id} to {agent_email} ({team})...")
    
    # 1. Update the Incident to "On Hold" and assign to the L1/L2 agent
    update_incident(
        ticket_id, 
        status="on hold", 
        # REMOVED assigned_to=agent_email  <-- This stops the email to Karen!
        assignment_group=team,
        comments=f"Automated System: Placed on hold pending manager approval from {manager_email}. Proposed assignee: {agent_email}. Reason: {reason}"
    )
    
    # 2. Get SysIDs securely from ServiceNow
    from mcp_server.tools.servicenow import get_sysid_by_query, INSTANCE, USER, PWD
    import requests
    from requests.auth import HTTPBasicAuth
    
    inc_id = get_sysid_by_query("incident", f"number={ticket_id}")
    mgr_id = get_sysid_by_query("sys_user", f"email={manager_email}")
    
    print(f"   ↳ DEBUG: Ticket SysID: '{inc_id}'")
    print(f"   ↳ DEBUG: Manager SysID: '{mgr_id}'")
    
    if not inc_id or not mgr_id:
        return f"⚠️ Missing SysID. Ticket='{inc_id}', Manager='{mgr_id}'"

    # 3. CALL THE CUSTOM SCRIPTED REST API
    # Using the exact namespace '1920142' from your ServiceNow instance
    approval_url = f"https://{INSTANCE}/api/1920142/teams_bot_api/create_approval"
    
    # The payload keys MUST match the variables in your JavaScript exactly!
    payload = {
        "manager_sys_id": str(mgr_id).strip(),
        "incident_sys_id": str(inc_id).strip()
    }
    
    headers = {
        "Content-Type": "application/json", 
        "Accept": "application/json"
    }
    
    # Send the POST request to your custom endpoint
    res = requests.post(approval_url, auth=HTTPBasicAuth(USER, PWD), headers=headers, json=payload)
    
    # 4. Handle the Response
    if res.status_code == 201:
        print(f"   ↳ ✅ Custom API Success! Approval Record Created.")
        return f"✅ Ticket {ticket_id} placed On Hold. Approval request successfully generated for {manager_email}."
    else:
        print(f"   ↳ ❌ Failed to create approval: {res.text}")
        return f"⚠️ Failed to create approval record: {res.text}"

@mcp.tool()
def get_ticket_approval_status(ticket_id: str) -> str:
    """
    Checks if the manager has clicked Approve or Reject in the ServiceNow email.
    Returns: 'requested', 'approved', 'rejected', or 'none'.
    """
    status = check_approval_status(ticket_id)
    print(f"   ↳ 🔎 Checked SNOW approval for {ticket_id}: {status.upper()}")
    return status

if __name__ == "__main__":
    mcp.run(transport="sse")