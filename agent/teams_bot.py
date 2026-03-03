import os
import json
import traceback
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes

# Import Agent dependencies
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

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

class ITSMBot(ActivityHandler):
    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """Welcomes the user."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text("👋 Hello! Tell me your issue (to create a ticket) or tell me a ticket ID is resolved."))

    async def on_message_activity(self, turn_context: TurnContext):
        """Main Chat Loop."""
        user_input = turn_context.activity.text
        
        # Send Typing Indicator
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        try:
            # Connect to MCP Server
            async with sse_client(MCP_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # A. Load Tools
                    tools = await session.list_tools()
                    openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools.tools]

                    # B. Prepare Messages (UPDATED SYSTEM PROMPT)
                    messages = [
                        {"role": "system", "content": """
                         You are a Direct IT Support Bot.
                         
                         YOUR RULES:
                         1. IF CREATING A TICKET:
                            - User reports an issue.
                            - First, call 'lookup_sla_policy' to check priority.
                            - Then, IMMEDIATELY call 'create_ticket'.
                            - Do NOT ask the user for a title. Summarize their message yourself for the 'description' argument.
                            - Return the Ticket ID.
                            
                         2. IF RESOLVING A TICKET:
                            - User says a ticket is fixed/resolved.
                            - Call 'update_incident' (or the available update tool) to set the status to 'Resolved'.
                            - If the user didn't provide the Ticket ID (e.g., INC1234), ask for it.
                         """},
                        {"role": "user", "content": user_input}
                    ]

                    # C. Thinking Loop
                    while True:
                        response = await CLIENT.chat.completions.create(
                            model=DEPLOYMENT, messages=messages, tools=openai_tools, tool_choice="auto"
                        )
                        msg = response.choices[0].message
                        
                        # CASE 1: Agent speaks to User
                        if not msg.tool_calls:
                            await turn_context.send_activity(MessageFactory.text(msg.content))
                            break
                        
                        # CASE 2: Agent uses Tools
                        messages.append(msg)
                        for tool in msg.tool_calls:
                            # Notify Teams User
                            await turn_context.send_activity(MessageFactory.text(f"⚙️ Action: `{tool.function.name}`..."))
                            
                            args = json.loads(tool.function.arguments)
                            result = await session.call_tool(tool.function.name, arguments=args)
                            
                            messages.append({
                                "role": "tool", "tool_call_id": tool.id, 
                                "name": tool.function.name, "content": result.content[0].text
                            })

        except Exception as e:
            print(f"❌ Error: {e}")
            await turn_context.send_activity(MessageFactory.text(f"⚠️ Error: {str(e)}"))