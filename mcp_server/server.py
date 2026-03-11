import json # <--- Make sure json is imported
import random
from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import create_incident, get_unassigned_tickets, update_incident, test_connection, get_tickets
from mcp_server.tools.email_service import send_approval_email
from mcp_server.tools import approval_tracker

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
    Returns JSON string containing agent, manager, and assignment group details.
    """
    result_dict = find_best_assignee(description)
    return json.dumps(result_dict)

@mcp.tool()
def assign_ticket(ticket_id: str, email: str, assignment_group: str = None) -> str:
    if not assignment_group:
        tickets = get_tickets({"number": ticket_id})
        if isinstance(tickets, list) and tickets:
            desc = tickets[0].get("desc", "")
            fallback = find_best_assignee(desc)
            assignment_group = fallback.get("assignment_group")
    return update_incident(ticket_id, assigned_to=email, assignment_group=assignment_group, status="in progress")

@mcp.tool()
def request_manager_approval(
    manager_email: str,
    ticket_id: str,
    reason: str,
    agent_email: str,
    assignment_group: str = None,
) -> str:
    """
    Sends an approval email to the manager.
    Returns a status message.
    """
    if approval_tracker.is_pending(ticket_id):
        return f"Approval already pending for {ticket_id}. Waiting for manager response."

    print(f"📧 Sending approval email to {manager_email} for ticket {ticket_id}")
    
    if not assignment_group:
        tickets = get_tickets({"number": ticket_id})
        if isinstance(tickets, list) and tickets:
            desc = tickets[0].get("desc", "")
            derived = find_best_assignee(desc)
            assignment_group = derived.get("assignment_group")
    
    success = send_approval_email(
        manager_email=manager_email,
        ticket_id=ticket_id,
        priority="1 - Critical",
        description=reason,
        agent_email=agent_email,
        assignment_group=assignment_group
    )
    
    if success:
        approval_tracker.mark_pending(ticket_id, manager_email, agent_email, assignment_group)
        return f"Email sent to {manager_email}. Ticket {ticket_id} is pending manager approval."
    else:
        return f"Failed to send approval email to {manager_email}. Check SMTP configuration."

if __name__ == "__main__":
    mcp.run(transport="sse")
