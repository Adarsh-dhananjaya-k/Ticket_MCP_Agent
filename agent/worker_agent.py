


import asyncio
import os
import json
import time
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

MCP_URL = "http://localhost:8000/sse"
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
CLIENT = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

async def run_worker():
    print("👷 P1-Aware Worker Started. Waiting for work...")
    
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            tools = await session.list_tools()
            openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools.tools]

            # --- SYSTEM PROMPT ---
            system_prompt = """
            You are an Autonomous IT Back-Office Worker.
            
            YOUR PROCESS HAS TWO PHASES:
            
            PHASE 1: DISPATCH NEW TICKETS
            1. Call 'fetch_new_work' to find unassigned tickets.
            2. For each ticket:
               - Call 'find_assignee' to get the agent_email, manager_email, and team.
               - IF PRIORITY IS '1': Call 'request_manager_approval' passing the agent_email, manager_email, team, ticket_id, and reason. Once requested, STOP processing this ticket (it is now On Hold).
               - IF PRIORITY IS NOT '1': Directly call 'assign_ticket' passing the ticket_id, email, and team.
            
            PHASE 2: CHECK PENDING APPROVALS
            1. Call 'list_tickets' with arguments {"priority": "1", "state": "3"} (State 3 means On Hold).
            2. For each ticket found:
               - Call 'get_ticket_approval_status' using the ticket_id.
               - IF status is 'approved': 
                    First, call 'find_assignee' using the ticket's short description to find the best agent. 
                    Then, call 'assign_ticket' to officially assign it to that agent's email! This will trigger their assignment email.
               - IF status is 'rejected': 
                    Call 'update_ticket' passing the ticket_id, status='in progress', and comments="Manager rejected the assignment. Ticket returning to queue."
               - IF status is 'requested': DO NOTHING. The manager hasn't clicked approve or reject yet.
            """

            while True:
                print("\n⏰ Checking for tickets...")
                messages = [{"role": "system", "content": system_prompt}]
                messages.append({"role": "user", "content": "Fetch tickets and process them according to priority rules."})

                while True:
                    await asyncio.sleep(1) # Prevent rate limit issues
                    try:
                        response = await CLIENT.chat.completions.create(model=DEPLOYMENT, messages=messages, tools=openai_tools)
                        msg = response.choices[0].message
                        
                        if not msg.tool_calls:
                            print(f"👷 Agent: {msg.content}")
                            break
                        
                        messages.append(msg)
                        for tool in msg.tool_calls:
                            t_name = tool.function.name
                            t_args = json.loads(tool.function.arguments)
                            print(f"   ⚙️ Tool: {t_name} | Args: {t_args}")
                            
                            result = await session.call_tool(t_name, arguments=t_args)
                            
                            # Print tool output for debugging
                            output_text = result.content[0].text
                            # Truncate long outputs for display
                            print(f"      ↳ Result: {output_text[:100]}...")
                            
                            messages.append({"role": "tool", "tool_call_id": tool.id, "name": t_name, "content": output_text})
                    
                    except Exception as e:
                        print(f"❌ Error in loop: {e}")
                        break

                print("💤 Sleeping 15s...")
                await asyncio.sleep(15)

if __name__ == "__main__":
    asyncio.run(run_worker())


