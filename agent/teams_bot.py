



import os
import json
from botbuilder.core import (
    ActivityHandler, 
    TurnContext, 
    MessageFactory, 
    ConversationState
)
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from botbuilder.core.teams import TeamsInfo
from botbuilder.schema import ConversationReference

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
    def __init__(self, conversation_state: ConversationState, conversation_references: dict):
        """
        Initialize the bot with ConversationState to handle memory.
        """
        if conversation_state is None:
            raise TypeError("[ITSMBot]: Missing parameter. conversation_state is required")

        self.conversation_state = conversation_state
        # Create an accessor to read/write the "History" key in memory
        self.history_accessor = self.conversation_state.create_property("History")

        self.conversation_references = conversation_references

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

        try:
            member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
            user_name = member.name or "Unknown User"
            user_email = member.email or member.user_principal_name or "unknown@email.com"
        except Exception as e:
            print(f"Could not fetch Teams user info: {e}")
            user_name = turn_context.activity.from_property.name
            user_email = "unknown_external_user@domain.com"
        
        conversation_reference = TurnContext.get_conversation_reference(turn_context.activity)
        self.conversation_references[user_email] = conversation_reference
        
        # 1. Retrieve Conversation History
        history = await self.history_accessor.get(turn_context, lambda: [])

        # 2. If History is empty, inject System Prompt
        if not history:
            history.append({
                "role": "system", 
                "content": f"""
                You are an intelligent IT Service Desk Assistant for Microsoft Teams.
                You are currently talking to {user_name} ({user_email}).
                
                YOUR CORE WORKFLOW FOR NEW ISSUES:
                When a user reports a new issue, you MUST follow these exact steps in order:
                
                1. CHECK PRIORITY: Call the 'lookup_sla_policy' tool using the user's description to determine if this is Critical (P1) or Standard. 
                   - Critical = impact "1", urgency "1"
                   - Standard = impact "3", urgency "3"
                   
                2. FIND ASSIGNEE: Call the 'find_assignee' tool using the issue description. This queries ServiceNow for real-time team workloads and returns the best 'suggested_agent_email' and the 'team'.
                
                3. CREATE TICKET: Call the 'create_ticket' tool. You MUST pass:
                   - description: Summarize the user's issue clearly.
                   - caller_email: Pass '{user_email}' exactly as written here.
                   - impact & urgency: Based on step 1.
                   - suggested_engineer_email: From step 2.
                   - assignment_group: The 'team' from step 2.
                
                4. IF P1/CRITICAL: You MUST immediately call the request_manager_approval tool using the returned manager_email, agent_email, team, and ticket_id to trigger the email.
                   
                5. INFORM THE USER: 
                   - Give them the resulting Ticket ID.
                   - If it is a P1/Critical ticket, explicitly state: "This is a Critical Priority issue. It has been placed On Hold while an email is sent to the team manager to approve the AI-suggested assignment."
                   - If it is standard, simply tell them the ticket has been routed to the [Team Name].
                
                YOUR RULES FOR RESOLVING TICKETS:
                - If a user says their issue is fixed/resolved, ask for the Ticket ID if they didn't provide one.
                - Call 'update_ticket' passing the ticket_id, action_by_email (MUST be '{user_email}'), status="resolved", and a brief comment.
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


