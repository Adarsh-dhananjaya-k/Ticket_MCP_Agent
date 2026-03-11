import asyncio
import os
import json
import traceback
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI

load_dotenv()

# --- CONFIGURATION ---
MCP_URL = "http://localhost:8000/sse"
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# OpenAI Client
CLIENT = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

async def chat_loop():
    print("\n--- 🤖 ITSM CLI Chat Agent Started ---")
    print("Type 'exit' or 'quit' to stop.\n")
    
    # Initialize history with the system prompt
    history = [
        {"role": "system", "content": """
        You are a Direct IT Support Bot.
        
        YOUR RULES:
        1. IF CREATING A TICKET:
           - User reports an issue.
           - First, call 'lookup_sla_policy' to check priority.
           - Then, IMMEDIATELY call 'create_ticket'.
           - Do NOT ask the user for a title. Summarize their message yourself for the 'description' argument.
           - Return the Ticket ID to the user.
           
        2. IF RESOLVING A TICKET:
           - User says a ticket is fixed/resolved.
           - Call 'update_ticket' to set the status to 'Resolved'.
           - If the user didn't provide the Ticket ID (e.g., INC1234), ask for it.
        3. WHEN ASSIGNING OR REQUESTING APPROVAL:
           - Always call 'find_assignee' first to get agent + assignment_group details.
           - Whenever you call 'assign_ticket' or 'request_manager_approval', include the 'assignment_group' returned by 'find_assignee'.
        """}
    ]

    try:
        # Connect to MCP Server
        async with sse_client(MCP_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Load Tools from MCP
                tools_data = await session.list_tools()
                openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools_data.tools]

                while True:
                    user_input = input("👤 You: ")
                    if user_input.lower() in ["exit", "quit"]:
                        break
                    
                    history.append({"role": "user", "content": user_input})
                    print("🤔 Thinking...")

                    while True:
                        # Call OpenAI
                        response = await CLIENT.chat.completions.create(
                            model=DEPLOYMENT, 
                            messages=history, 
                            tools=openai_tools, 
                            tool_choice="auto"
                        )
                        msg = response.choices[0].message
                        
                        # Add Agent response to history
                        history.append(msg)
                        
                        # CASE 1: Agent speaks to User
                        if not msg.tool_calls:
                            print(f"🤖 Bot: {msg.content}")
                            break
                        
                        # CASE 2: Agent uses Tools
                        for tool in msg.tool_calls:
                            t_name = tool.function.name
                            t_args = json.loads(tool.function.arguments)
                            print(f"⚙️ Running Tool: {t_name}...")
                            
                            try:
                                result = await session.call_tool(t_name, arguments=t_args)
                                tool_output = result.content[0].text
                                
                                history.append({
                                    "role": "tool", 
                                    "tool_call_id": tool.id, 
                                    "name": t_name, 
                                    "content": tool_output
                                })
                            except Exception as tool_err:
                                print(f"❌ Tool Error: {tool_err}")
                                history.append({
                                    "role": "tool", 
                                    "tool_call_id": tool.id, 
                                    "name": t_name, 
                                    "content": f"Error: {str(tool_err)}"
                                })

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(chat_loop())
