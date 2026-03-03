from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import create_incident, get_unassigned_tickets, update_incident, test_connection, get_tickets

mcp = FastMCP("ITSM-System")

@mcp.tool()
def connection_test() -> str:
    """Validate connection to ServiceNow."""
    return test_connection()

@mcp.tool()
def list_tickets(priority: str = None, state: str = None, ticket_id: str = None) -> str:
    """Fetch tickets from ServiceNow. Filter by priority (1-4), state (1-8), or find a specific ticket_id (e.g. INC0010008)."""
    import json
    query = {}
    if ticket_id: query["number"] = ticket_id # Search by exact ID
    if priority: query["priority"] = priority
    if state: query["state"] = state
    return json.dumps(get_tickets(query))

# --- Chat Agent Tools ---
@mcp.tool()
def lookup_sla_policy(description: str) -> str:
    """Check Priority (P1-P4) using Azure Search."""
    return lookup_sla(description)

@mcp.tool()
def create_ticket(description: str, impact: str = "3", urgency: str = "3") -> str:
    """
    Create a new ticket in ServiceNow.
    Impact/Urgency: 1 (High), 2 (Medium), 3 (Low).
    ServiceNow calculates priority automatically from these.
    """
    return create_incident(description, impact=impact, urgency=urgency)

# --- Worker Agent Tools ---
@mcp.tool()
def fetch_new_work() -> str:
    """Get list of unassigned tickets."""
    import json
    return json.dumps(get_unassigned_tickets())

@mcp.tool()
def update_ticket(ticket_id: str, status: str = None, impact: str = None, urgency: str = None, assigned_to: str = None, comments: str = None) -> str:
    """
    Update specific fields of an existing ServiceNow ticket.
    - status: 'open', 'in progress', 'on hold', 'resolved', 'closed', 'canceled'
    - impact/urgency: '1' (High), '2' (Medium), '3' (Low)
    - assigned_to: Name or SysID of the agent
    - comments: Text to add to the ticket's history
    """
    kwargs = {k: v for k, v in locals().items() if v is not None and k != "ticket_id"}
    return update_incident(ticket_id, **kwargs)


@mcp.tool()
def find_assignee(description: str) -> str:
    """Find best agent email based on roster workload."""
    return find_best_assignee(description)

@mcp.tool()
def assign_ticket(ticket_id: str, email: str) -> str:
    """Assign ticket to a specific email."""
    return update_incident(ticket_id, assigned_to=email, status="Assigned")

if __name__ == "__main__":
    mcp.run(transport="sse")