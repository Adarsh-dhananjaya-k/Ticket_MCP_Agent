from mcp.server.fastmcp import FastMCP
from mcp_server.tools.sla_policy import lookup_sla

# 🚀 FIX: Pass host and port into the FastMCP constructor!
mcp = FastMCP("Azure-Utilities", host="127.0.0.1", port=8001)

@mcp.tool()
def lookup_sla_policy(description: str) -> str:
    """
    Queries the SLA policy documents in Azure AI Search to determine 
    if an IT issue should be classified as Critical (P1) or Standard.
    """
    return lookup_sla(description)

if __name__ == "__main__":
    print("🚀 Starting Azure MCP Server on port 8001...")
    # 🚀 FIX: .run() only takes the transport argument now
    mcp.run(transport="sse")