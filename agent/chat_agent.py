import asyncio
import os
import sys
import json
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

async def run_chat():
    print("💬 Chat Agent Started. Connecting to Server...")
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Tools Setup
            tools = await session.list_tools()
            openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools.tools]
            
            messages = [{
                "role": "system", 
                "content": "You are IT Support. 1. Ask issue. 2. Call lookup_sla_policy. 3. Determine the correct Impact (1-3) and Urgency (1-3) from that policy. 4. Call create_ticket. 5. Give Ticket ID."
            }]

            while True:
                user_msg = input("\n👤 User: ")
                if user_msg.lower() == "quit": break
                messages.append({"role": "user", "content": user_msg})

                while True:
                    response = await CLIENT.chat.completions.create(model=DEPLOYMENT, messages=messages, tools=openai_tools)
                    msg = response.choices[0].message
                    
                    if not msg.tool_calls:
                        print(f"🤖 Agent: {msg.content}")
                        messages.append(msg)
                        break
                    
                    messages.append(msg)
                    for tool in msg.tool_calls:
                        print(f"   ⚙️ Tool: {tool.function.name}...")
                        args = json.loads(tool.function.arguments)
                        result = await session.call_tool(tool.function.name, arguments=args)
                        messages.append({"role": "tool", "tool_call_id": tool.id, "name": tool.function.name, "content": result.content[0].text})

if __name__ == "__main__":
    asyncio.run(run_chat())