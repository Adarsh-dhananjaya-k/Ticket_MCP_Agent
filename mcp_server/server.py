import json
import secrets
from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import get_sysid_by_query, get_user_sysid
from mcp_server.tools.servicenow import (
    create_incident, 
    update_incident, 
    get_tickets, 
    check_approval_status
)
from mcp_server.tools.servicenow import get_agent_workload

mcp = FastMCP("ITSM-System")

@mcp.tool()
def list_tickets(priority: str = None, state: str = None, ticket_id: str = None, assignment_group: str = None, assigned_to_email: str = None) -> str:
    """
    Get real-time details of tickets from ServiceNow.
    Can filter by priority, state, ticket_id, assignment_group (e.g. 'Software_Support'), and assigned_to_email.
    Returns a JSON list.
    """
    query = {}
    if ticket_id: query["number"] = ticket_id
    if priority: query["priority"] = priority
    if state: query["state"] = state
    
    # 🔥 THE FIX: Translate the Group Name into a ServiceNow SysID first!
    if assignment_group: 
        safe_group_name = assignment_group.replace(" ", "_")
        group_sysid = get_sysid_by_query("sys_user_group", f"name={safe_group_name}")
        if group_sysid:
            query["assignment_group"] = group_sysid
        else:
            return "[]" # Group not found in SNOW

    # Do the same for the email just to be perfectly safe
    if assigned_to_email:
        user_sysid = get_user_sysid(assigned_to_email)
        if user_sysid:
            query["assigned_to"] = user_sysid
        else:
            return "[]" # User not found in SNOW

    # Finally, execute the search and return the JSON!
    return json.dumps(get_tickets(query))

@mcp.tool()
def check_agent_workload(agent_email: str) -> str:
    """
    Returns the exact number of active tickets currently assigned to a specific agent's email.
    Use this when the user asks how many tickets a specific person has.
    """
    count = get_agent_workload(agent_email)
    return f"{agent_email} currently has {count} active tickets assigned to them."

@mcp.tool()
def lookup_sla_policy(description: str) -> str:
    """Queries the SLA policy documents to determine if an issue is Critical or Standard."""
    return lookup_sla(description)

@mcp.tool()
def create_ticket(description: str, impact: str = "3", urgency: str = "3", suggested_engineer_email: str = None, assignment_group: str = None, caller_email: str = None) -> str:
    """
    Creates a ticket in ServiceNow. 
    Ensure you pass the caller_email of the user requesting help.
    If you know the best assignee and team, provide `suggested_engineer_email` and `assignment_group`.
    For Priority 1 issues (Impact=1, Urgency=1), the system will automatically place the ticket 'On Hold' for manager approval.
    """
    return create_incident(
        description, 
        impact=impact, 
        urgency=urgency, 
        suggested_engineer_email=suggested_engineer_email,
        assignment_group=assignment_group,
        caller_email=caller_email
    )

@mcp.tool()
def update_ticket(ticket_id: str, action_by_email: str, status: str = None, assigned_to: str = None, comments: str = None) -> str:
    """
    Update ticket details (like resolving a ticket).
    IMPORTANT: You MUST pass 'action_by_email' (the email of the user you are currently chatting with).
    """
    kwargs = {k: v for k, v in locals().items() if v is not None and k not in["ticket_id", "action_by_email"]}
    return update_incident(ticket_id, action_by_email=action_by_email, **kwargs)

@mcp.tool()
def find_assignee(description: str, priority: str = "Standard", caller_email: str = None) -> str:
    """
    Queries real-time workloads and skills to find the best agent. 
    Returns JSON string with best agent details. Priority should be 'Critical' or 'Standard'.
    ALWAYS pass the caller_email so the system doesn't assign the ticket to the person reporting it!
    """
    result_dict = find_best_assignee(description, priority, caller_email)
    return json.dumps(result_dict)

@mcp.tool()
def request_manager_approval(agent_email: str, manager_email: str, team: str, ticket_id: str, reason: str) -> str:
    """Assigns ticket, puts it On Hold, and creates Approval Record via Custom API."""
    print(f"\n⚙️[APPROVAL] Assigning {ticket_id} to {agent_email} ({team})...")
    
    # 1. Update the Incident to "On Hold" and assign to the team
    update_incident(
        ticket_id, 
        status="on hold", 
        assignment_group=team,
        comments=f"Automated System: Placed on hold pending manager approval from {manager_email}. Proposed assignee: {agent_email}. Reason: {reason}"
    )

    # 2. GENERATE THE SECURE TOKEN
    approval_token = secrets.token_urlsafe(32) 
    
    # 3. Get SysIDs securely from ServiceNow
    from mcp_server.tools.servicenow import get_sysid_by_query, INSTANCE, USER, PWD
    import requests
    from requests.auth import HTTPBasicAuth
    
    inc_id = get_sysid_by_query("incident", f"number={ticket_id}")
    mgr_id = get_sysid_by_query("sys_user", f"email={manager_email}")
    
    if not inc_id or not mgr_id:
        return f"⚠️ Missing SysID. Ticket='{inc_id}', Manager='{mgr_id}'"

    # 4. CALL THE CUSTOM SCRIPTED REST API
    approval_url = f"https://{INSTANCE}/api/1920142/teams_bot_api/create_approval"
    
    payload = {
        "manager_sys_id": str(mgr_id).strip(),
        "incident_sys_id": str(inc_id).strip(),
        "approval_token": approval_token
    }
    
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    
    res = requests.post(approval_url, auth=HTTPBasicAuth(USER, PWD), headers=headers, json=payload)
    
    if res.status_code == 201:
        return f"✅ Ticket {ticket_id} placed On Hold. Approval request successfully generated for {manager_email}."
    else:
        return f"⚠️ Failed to create approval record: {res.text}"

@mcp.tool()
def get_ticket_approval_status(ticket_id: str) -> str:
    """
    Checks if the manager has clicked Approve or Reject in the ServiceNow email.
    It will return the approval status AND the name of the user who actually got assigned the ticket.
    """
    status = check_approval_status(ticket_id)
    return status

if __name__ == "__main__":
    mcp.run(transport="sse")