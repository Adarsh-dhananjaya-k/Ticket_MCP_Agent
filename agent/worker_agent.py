import asyncio
import os
import json
import time
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

load_dotenv()

# Config
MCP_URL = "http://localhost:8000/sse"
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")
CLIENT = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

async def run_worker():
    print("👷 Auto-Worker Started. Waiting for tickets...")
    
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Tools Setup
            tools = await session.list_tools()
            openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools.tools]

            # The Worker's Brain
            system_prompt = """
            You are an Autonomous Back-Office Worker.
            Your Goal: Process unassigned tickets.
            
            Loop Logic:
            1. Call 'fetch_new_work'.
            2. If tickets found:
               a. For each ticket, read the description.
               b. Call 'find_assignee' to get the best email from the roster.
               c. Call 'assign_ticket' to update the record.
            3. If no tickets, just say "No work found".
            """

            while True:
                print("\n⏰ Worker Waking Up...")
                messages = [{"role": "system", "content": system_prompt}]
                
                # Trigger the agent to check work
                messages.append({"role": "user", "content": "Check for new tickets and process them."})

                # --- AGENT EXECUTION LOOP ---
                while True:
                    response = await CLIENT.chat.completions.create(model=DEPLOYMENT, messages=messages, tools=openai_tools)
                    msg = response.choices[0].message
                    
                    if not msg.tool_calls:
                        print(f"👷 Worker Log: {msg.content}")
                        break # Done for this cycle
                    
                    messages.append(msg)
                    for tool in msg.tool_calls:
                        t_name = tool.function.name
                        t_args = json.loads(tool.function.arguments)
                        print(f"   ⚙️ Executing: {t_name} {t_args}")
                        
                        result = await session.call_tool(t_name, arguments=t_args)
                        messages.append({"role": "tool", "tool_call_id": tool.id, "name": t_name, "content": result.content[0].text})

                print("💤 Sleeping for 15 seconds...")
                time.sleep(15) # Wait before next check

if __name__ == "__main__":
    asyncio.run(run_worker())