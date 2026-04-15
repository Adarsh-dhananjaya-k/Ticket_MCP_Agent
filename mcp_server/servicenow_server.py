import json
import secrets
from mcp.server.fastmcp import FastMCP

from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import (
    get_sysid_by_query, get_user_sysid, get_agent_workload,
    create_incident, update_incident, get_tickets, check_approval_status,upload_user_image_to_ticket,search_active_issues 
)

# 🚀 FIX: Pass host and port into the FastMCP constructor!
mcp = FastMCP("ServiceNow-Tools", host="127.0.0.1", port=8000)

@mcp.tool()
def list_tickets(priority: str = None, state: str = None, ticket_id: str = None, assignment_group: str = None, assigned_to_email: str = None) -> str:
    """Get real-time details of tickets from ServiceNow."""
    query = {}
    if ticket_id: query["number"] = ticket_id
    if priority: query["priority"] = priority
    if state: query["state"] = state
    
    if assignment_group: 
        safe_group = assignment_group.replace(" ", "_")
        group_sysid = get_sysid_by_query("sys_user_group", f"name={safe_group}")
        if group_sysid: query["assignment_group"] = group_sysid
        else: return "[]"

    if assigned_to_email:
        user_sysid = get_user_sysid(assigned_to_email)
        if user_sysid: query["assigned_to"] = user_sysid
        else: return "[]"

    return json.dumps(get_tickets(query))

@mcp.tool()
def check_agent_workload(agent_email: str) -> str:
    count = get_agent_workload(agent_email)
    return f"{agent_email} has {count} active tickets."

@mcp.tool()
def create_ticket(description: str, impact: str = "3", urgency: str = "3", suggested_engineer_email: str = None, assignment_group: str = None, caller_email: str = None) -> str:
    return create_incident(description, impact=impact, urgency=urgency, suggested_engineer_email=suggested_engineer_email, assignment_group=assignment_group, caller_email=caller_email)

@mcp.tool()
def update_ticket(ticket_id: str, action_by_email: str, status: str = None, assigned_to: str = None, comments: str = None, add_to_watchlist: bool = False) -> str: # 🚀 ADDED add_to_watchlist
    kwargs = {k: v for k, v in locals().items() if v is not None and k not in["ticket_id", "action_by_email"]}
    return update_incident(ticket_id, action_by_email=action_by_email, **kwargs)

@mcp.tool()
def find_assignee(description: str, priority: str = "Standard", caller_email: str = None) -> str:
    return json.dumps(find_best_assignee(description, priority, caller_email))

@mcp.tool()
def request_manager_approval(agent_email: str, manager_email: str, team: str, ticket_id: str, reason: str) -> str:
    """Assigns ticket, puts it On Hold, and creates Approval Record via Custom API."""
    print(f"\n⚙️[APPROVAL] Assigning {ticket_id} to {agent_email} ({team})...")
    
    update_incident(
        ticket_id, 
        status="on hold", 
        assignment_group=team,
        comments=f"Automated System: Placed on hold pending manager approval from {manager_email}. Proposed assignee: {agent_email}. Reason: {reason}"
    )

    approval_token = secrets.token_urlsafe(32) 
    
    from mcp_server.tools.servicenow import INSTANCE, USER, PWD
    import requests
    from requests.auth import HTTPBasicAuth
    
    inc_id = get_sysid_by_query("incident", f"number={ticket_id}")
    mgr_id = get_sysid_by_query("sys_user", f"email={manager_email}")
    
    if not inc_id or not mgr_id:
        return f"⚠️ Missing SysID. Ticket='{inc_id}', Manager='{mgr_id}'"

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
    return check_approval_status(ticket_id)

@mcp.tool()
def attach_image_to_ticket(ticket_id: str, caller_email: str) -> str:
    """
    ALWAYS call this immediately after creating a ticket if the user previously uploaded an image or screenshot.
    Uploads the user's most recently shared image to the specified ServiceNow ticket.
    """
    return upload_user_image_to_ticket(ticket_id, caller_email)

@mcp.tool()
def check_active_outages(keyword: str) -> str:
    """
    Searches ServiceNow for currently active/open incidents matching a specific keyword (e.g., 'React', 'VPN', 'Outlook').
    Use this to check for duplicate global issues before creating a new ticket.
    """
    return search_active_issues(keyword)

if __name__ == "__main__":
    print("🚀 Starting ServiceNow MCP Server on port 8000...")
    # 🚀 FIX: .run() only takes the transport argument now
    mcp.run(transport="sse")