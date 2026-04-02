import os
import json
import traceback
from contextlib import AsyncExitStack

from botbuilder.core import (
    ActivityHandler, 
    TurnContext, 
    MessageFactory, 
    ConversationState
)
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from botbuilder.core.teams import TeamsInfo

# Import Agent dependencies
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# 🚀 PHASE 5: Import DB Logging
from agent.db import log_interaction

load_dotenv()

# --- AZURE OPENAI CLIENT SETUP ---
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

CLIENT = AsyncAzureOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION")
)

class ITSMBot(ActivityHandler):
    def __init__(self, conversation_state: ConversationState, conversation_references: dict):
        """
        Initialize the bot with state management and multi-server config.
        """
        if conversation_state is None:
            raise TypeError("[ITSMBot]: Missing parameter. conversation_state is required")

        self.conversation_state = conversation_state
        self.history_accessor = self.conversation_state.create_property("History")
        self.conversation_references = conversation_references

        # 🚀 PHASE 1: Load the Master Configuration
        self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_config.json"))
        try:
            with open(self.config_path, "r") as f:
                self.mcp_config = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ WARNING: {self.config_path} not found. Creating empty config in memory.")
            self.mcp_config = {"mcp_servers":[]}

    # 🚀 PHASE 2: Dynamic Prompt Loader
    def _load_system_prompt(self, user_name: str, user_email: str) -> str:
        """Reads external text files from the 'prompts' directory and compiles the System Prompt."""
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))
        
        try:
            with open(os.path.join(base_dir, "base.txt"), "r", encoding="utf-8") as f:
                base_prompt = f.read().strip()
                
            with open(os.path.join(base_dir, "system.txt"), "r", encoding="utf-8") as f:
                system_prompt = f.read().strip()
                
            with open(os.path.join(base_dir, "business_rules.txt"), "r", encoding="utf-8") as f:
                business_rules = f.read().strip()
                
        except Exception as e:
            print(f"⚠️ Error loading prompts: {e}. Falling back to default system prompt.")
            return f"You are an IT Assistant. You are currently talking to {user_name} ({user_email})."

        # Dynamically inject the user context into the prompt
        compiled_prompt = f"""
{base_prompt}

=== LIVE CHAT CONTEXT ===
You are currently talking to {user_name}.
Their official email address is: {user_email}.
Use this exact email when tools require a 'caller_email' or 'action_by_email'.

{system_prompt}

{business_rules}
"""
        return compiled_prompt.strip()

    async def on_turn(self, turn_context: TurnContext):
        """Runs on every turn. Ensures state is saved at the end of the turn."""
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """Greets new users when they start a chat."""
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text("👋 Hello! I am your AI IT Assistant. How can I help you today?")
                )

    async def on_message_activity(self, turn_context: TurnContext):
        """Main Chat Loop with Multi-MCP Routing & Advanced State Management."""
        user_input = turn_context.activity.text.strip()

        # 1. Fetch User Info (With Emulator Fallback)
        try:
            member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
            user_name = member.name or "Unknown User"
            user_email = member.email or member.user_principal_name or "unknown@email.com"
        except Exception:
            user_name = turn_context.activity.from_property.name or "Local Tester"
            user_email = "local_tester@domain.com"
        
        self.conversation_references[user_email] = TurnContext.get_conversation_reference(turn_context.activity)
        log_interaction(user_email, "user", user_input)

        # 2. Retrieve Conversation History from Azure Blob
        history = await self.history_accessor.get(turn_context, lambda:[])

        # =======================================================
        # 🚀 FIX 1: THE "START OVER" COMMAND (Context Confusion)
        # =======================================================
        # In ITSM, users switch topics (e.g., from Printer to Password).
        # We give them a magic phrase to wipe the bot's memory manually.
        if user_input.lower() in["start over", "clear", "new issue", "restart"]:
            history =[]  # Wipe the array clean
            await self.history_accessor.set(turn_context, history)
            await turn_context.send_activity(MessageFactory.text("🔄 Conversation history cleared. What new issue can I help you with today?"))
            return  # Stop processing here! Don't call OpenAI.

        # 3. Inject Externalized Prompt on First Message
        if not history:
            compiled_system_prompt = self._load_system_prompt(user_name, user_email)
            history.append({"role": "system", "content": compiled_system_prompt})

        # Append the new user message
        history.append({"role": "user", "content": user_input})

        # =======================================================
        # 🚀 FIX 2: THE "SLIDING WINDOW" (Token Bloat Protection)
        # =======================================================
        # Prevents OpenAI from crashing if the user chats 50+ times in a row.
        MAX_TURNS = 15  # Keep the System Prompt + the last 14 messages
        
        if len(history) > MAX_TURNS:
            system_prompt = history[0]
            
            # Slice the history to keep only the most recent messages
            recent_history = history[-(MAX_TURNS - 1):]
            
            # OpenAI Guardrail: NEVER orphan a 'tool' response. 
            # If the oldest message in our slice is a 'tool' result, we must drop it 
            # so OpenAI doesn't crash expecting the matching 'tool_call' request.
            while recent_history and recent_history[0].get("role") == "tool":
                recent_history.pop(0)
                
            history = [system_prompt] + recent_history
        # =======================================================

        # Send a typing indicator to Teams
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))
        try:
            # 🚀 PHASE 1: THE MULTI-SERVER ROUTER (AsyncExitStack) 🚀
            async with AsyncExitStack() as stack:
                
                active_sessions = {}    # Maps: server_name -> ClientSession object
                tool_routing_map = {}   # Maps: tool_name -> server_name
                openai_tools =[]       # Master list of all tools for the LLM

                # 5. Dynamically connect to all ENABLED servers
                for server in self.mcp_config.get("mcp_servers",[]):
                    if not server.get("enabled"):
                        continue
                    
                    server_name = server["name"]
                    server_url = server["url"]

                    try:
                        print(f"🔌 Connecting to Microservice: {server_name} at {server_url}")
                        read, write = await stack.enter_async_context(sse_client(server_url))
                        session = await stack.enter_async_context(ClientSession(read, write))
                        await session.initialize()
                        
                        active_sessions[server_name] = session

                        # Fetch tools from this specific server and build the Routing Map
                        tools_response = await session.list_tools()
                        for t in tools_response.tools:
                            tool_routing_map[t.name] = server_name
                            openai_tools.append({
                                "type": "function", 
                                "function": {
                                    "name": t.name, 
                                    "description": t.description, 
                                    "parameters": t.inputSchema
                                }
                            })
                            
                    # 🚀 CRITICAL FIX: Catch Python 3.11+ TaskGroup ExceptionGroups!
                    except ExceptionGroup as eg:
                        print(f"❌ TaskGroup Error connecting to {server_name}: {eg}")
                        await turn_context.send_activity(
                            MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline. Some features may be unavailable.")
                        )
                    except Exception as e:
                        print(f"❌ Failed to connect to {server_name}: {e}")
                        await turn_context.send_activity(
                            MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline. Some features may be unavailable.")
                        )

                # Fail-safe if no tools loaded at all
                if not openai_tools:
                    await turn_context.send_activity(MessageFactory.text("❌ All backend systems are offline. I cannot process your request right now. Please try again later."))
                    return

                # --- 6. THE THINKING LOOP ---
                while True:
                    response = await CLIENT.chat.completions.create(
                        model=DEPLOYMENT, 
                        messages=history, 
                        tools=openai_tools, 
                        tool_choice="auto"
                    )
                    msg = response.choices[0].message
                    history.append(msg)
                    
                    # CASE A: AI replies directly to the user
                    if not msg.tool_calls:
                        # 🟢 PHASE 5: Log the bot's final reply
                        log_interaction(user_email, "bot", msg.content)
                        await turn_context.send_activity(MessageFactory.text(msg.content))
                        break
                    
                    # CASE B: AI requests tool execution
                    for tool in msg.tool_calls:
                        tool_name = tool.function.name
                        args = json.loads(tool.function.arguments)
                        
                        target_server_name = tool_routing_map.get(tool_name)
                        
                        if not target_server_name or target_server_name not in active_sessions:
                            err_msg = f"System Error: Tool '{tool_name}' requested but routing to '{target_server_name}' failed."
                            print(err_msg)
                            history.append({"role": "tool", "tool_call_id": tool.id, "name": tool_name, "content": err_msg})
                            continue

                        # Granular UI Feedback
                        friendly_name = tool_name.replace('_', ' ').title()
                        await turn_context.send_activity(MessageFactory.text(f"⚙️ *{friendly_name}*..."))
                        
                        # Execute the tool on the target server
                        try:
                            target_session = active_sessions[target_server_name]
                            result = await target_session.call_tool(tool_name, arguments=args)
                            tool_result_content = result.content[0].text
                            
                            # 🟢 PHASE 5: Log the tool execution result
                            log_interaction(user_email, "tool", tool_result_content, tool_name)
                            
                        except Exception as tool_err:
                            tool_result_content = f"Error executing tool: {str(tool_err)}"
                            print(f"❌ Tool Error ({tool_name}): {tool_err}")
                            log_interaction(user_email, "tool", tool_result_content, tool_name)
                        
                        # Return the result back to the AI's context
                        history.append({
                            "role": "tool", 
                            "tool_call_id": tool.id, 
                            "name": tool_name, 
                            "content": tool_result_content
                        })
            
            # 8. Save updated history to State
            await self.history_accessor.set(turn_context, history)

        except Exception as e:
            print("❌ Critical Chat Error:")
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"⚠️ Critical Error processing your request: {str(e)}"))