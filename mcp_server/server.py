from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools.servicenow import create_incident, get_unassigned_tickets, update_incident

mcp = FastMCP("ITSM-System")

# --- Chat Agent Tools ---
@mcp.tool()
def lookup_sla_policy(description: str) -> str:
    """Check Priority (P1-P4) using Azure Search."""
    return lookup_sla(description)

@mcp.tool()
def create_ticket(description: str, priority: str) -> str:
    """Create a new ticket in ServiceNow."""
    return create_incident(description, priority)

# --- Worker Agent Tools ---
@mcp.tool()
def fetch_new_work() -> str:
    """Get list of unassigned tickets."""
    import json
    return json.dumps(get_unassigned_tickets())

@mcp.tool()
def update_ticket(ticket_id, **kwargs):
    """Updates the ticket"""
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