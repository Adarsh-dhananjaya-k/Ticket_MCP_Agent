import json # <--- Make sure json is imported
import random
from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import create_incident, get_unassigned_tickets, update_incident, test_connection, get_tickets

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
def assign_ticket(ticket_id: str, email: str) -> str:
    return update_incident(ticket_id, assigned_to=email, status="Assigned")

# --- MOCK APPROVAL TOOL ---
@mcp.tool()
def request_manager_approval(manager_email: str, ticket_id: str, reason: str) -> str:
    """
    DEMO ONLY: Simulates sending an email to the manager.
    Returns 'Approved' or 'Rejected'.
    """
    print(f"\n📧 [DEMO EMAIL SENT]")
    print(f"   To: {manager_email}")
    print(f"   Subject: P1 Ticket Approval Needed ({ticket_id})")
    print(f"   Body: {reason}\n")
    
    # Randomly approve or reject for demo
    decision = random.choices(["Approved", "Rejected"], weights=[0.8, 0.2], k=1)[0]
    
    print(f"   📩 [MANAGER REPLIED]: {decision}\n")
    return decision

if __name__ == "__main__":
    mcp.run(transport="sse")