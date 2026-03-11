



import os
import json
from botbuilder.core import (
    ActivityHandler, 
    TurnContext, 
    MessageFactory, 
    ConversationState
)
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
    def __init__(self, conversation_state: ConversationState):
        """
        Initialize the bot with ConversationState to handle memory.
        """
        if conversation_state is None:
            raise TypeError("[ITSMBot]: Missing parameter. conversation_state is required")

        self.conversation_state = conversation_state
        # Create an accessor to read/write the "History" key in memory
        self.history_accessor = self.conversation_state.create_property("History")

    async def on_turn(self, turn_context: TurnContext):
        """
        Runs on every turn. We override this to ensure state is saved 
        at the end of the turn.
        """
        await super().on_turn(turn_context)
        # Save any changes to memory (critical!)
        await self.conversation_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text("👋 Hello! Tell me your issue (to create a ticket) or tell me a ticket ID is resolved."))

    async def on_message_activity(self, turn_context: TurnContext):
        """Main Chat Loop with Memory."""
        user_input = turn_context.activity.text
        
        # 1. Retrieve Conversation History
        history = await self.history_accessor.get(turn_context, lambda: [])

        # 2. If History is empty, inject System Prompt
        if not history:
            history.append({
                "role": "system", 
                "content": """
                You are a Direct IT Support Bot.
                
                YOUR RULES:
                1. IF CREATING A TICKET:
                   - User reports an issue.
                   - First, call 'lookup_sla_policy' to check priority.
                   - Then, IMMEDIATELY call 'create_ticket'.
                   - Do NOT ask the user for a title. Summarize their message yourself.
                   - Return the Ticket ID.
                   
                2. IF RESOLVING A TICKET:
                   - User says a ticket is fixed/resolved.
                   - Call 'update_incident' (or update tool).
                   - If Ticket ID is missing, ask for it.
                """
            })

        # 3. Append User Message
        history.append({"role": "user", "content": user_input})
        
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        try:
            # Connect to MCP Server
            async with sse_client(MCP_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Load Tools
                    tools = await session.list_tools()
                    openai_tools = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in tools.tools]

                    # --- Thinking Loop ---
                    while True:
                        # Call OpenAI with the FULL history
                        response = await CLIENT.chat.completions.create(
                            model=DEPLOYMENT, messages=history, tools=openai_tools, tool_choice="auto"
                        )
                        msg = response.choices[0].message
                        
                        # Add Agent Response to History (So it remembers what it proposed)
                        history.append(msg)
                        
                        # CASE 1: Agent speaks to User (No tools used)
                        if not msg.tool_calls:
                            await turn_context.send_activity(MessageFactory.text(msg.content))
                            break
                        
                        # CASE 2: Agent uses Tools
                        for tool in msg.tool_calls:
                            # --- CHANGED HERE: Send specific tool name to Teams ---
                            await turn_context.send_activity(MessageFactory.text(f"⚙️ Calling tool: {tool.function.name}..."))
                            
                            args = json.loads(tool.function.arguments)
                            result = await session.call_tool(tool.function.name, arguments=args)
                            
                            # Add Tool Result to History
                            history.append({
                                "role": "tool", 
                                "tool_call_id": tool.id, 
                                "name": tool.function.name, 
                                "content": result.content[0].text
                            })
            
            # 4. Save updated history to State
            await self.history_accessor.set(turn_context, history)

        except Exception as e:
            print(f"❌ Error: {e}")
            await turn_context.send_activity(MessageFactory.text(f"⚠️ Error: {str(e)}"))


