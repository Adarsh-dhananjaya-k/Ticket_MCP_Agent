# import os
# import json
# import traceback
# from contextlib import AsyncExitStack

# from botbuilder.core import (
#     ActivityHandler, 
#     TurnContext, 
#     MessageFactory, 
#     ConversationState
# )
# from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
# from botbuilder.core.teams import TeamsInfo

# # Import Agent dependencies
# from mcp import ClientSession
# from mcp.client.sse import sse_client
# from openai import AsyncAzureOpenAI
# from dotenv import load_dotenv

# # 🚀 PHASE 5: Import DB Logging
# from agent.db import log_interaction

# load_dotenv()

# # --- AZURE OPENAI CLIENT SETUP ---
# DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT")

# CLIENT = AsyncAzureOpenAI(
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
#     api_key=os.getenv("AZURE_OPENAI_KEY"),
#     api_version=os.getenv("AZURE_OPENAI_API_VERSION")
# )

# class ITSMBot(ActivityHandler):
#     def __init__(self, conversation_state: ConversationState, conversation_references: dict):
#         """
#         Initialize the bot with state management and multi-server config.
#         """
#         if conversation_state is None:
#             raise TypeError("[ITSMBot]: Missing parameter. conversation_state is required")

#         self.conversation_state = conversation_state
#         self.history_accessor = self.conversation_state.create_property("History")
#         self.conversation_references = conversation_references

#         # 🚀 PHASE 1: Load the Master Configuration
#         self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_config.json"))
#         try:
#             with open(self.config_path, "r") as f:
#                 self.mcp_config = json.load(f)
#         except FileNotFoundError:
#             print(f"⚠️ WARNING: {self.config_path} not found. Creating empty config in memory.")
#             self.mcp_config = {"mcp_servers":[]}

#     # 🚀 PHASE 2: Dynamic Prompt Loader
#     def _load_system_prompt(self, user_name: str, user_email: str) -> str:
#         """Reads external text files from the 'prompts' directory and compiles the System Prompt."""
#         base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))
        
#         try:
#             with open(os.path.join(base_dir, "base.txt"), "r", encoding="utf-8") as f:
#                 base_prompt = f.read().strip()
                
#             with open(os.path.join(base_dir, "system.txt"), "r", encoding="utf-8") as f:
#                 system_prompt = f.read().strip()
                
#             with open(os.path.join(base_dir, "business_rules.txt"), "r", encoding="utf-8") as f:
#                 business_rules = f.read().strip()
                
#         except Exception as e:
#             print(f"⚠️ Error loading prompts: {e}. Falling back to default system prompt.")
#             return f"You are an IT Assistant. You are currently talking to {user_name} ({user_email})."

#         # Dynamically inject the user context into the prompt
#         compiled_prompt = f"""
# {base_prompt}

# === LIVE CHAT CONTEXT ===
# You are currently talking to {user_name}.
# Their official email address is: {user_email}.
# Use this exact email when tools require a 'caller_email' or 'action_by_email'.

# {system_prompt}

# {business_rules}
# """
#         return compiled_prompt.strip()

#     async def on_turn(self, turn_context: TurnContext):
#         """Runs on every turn. Ensures state is saved at the end of the turn."""
#         await super().on_turn(turn_context)
#         await self.conversation_state.save_changes(turn_context)

#     async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
#         """Greets new users when they start a chat."""
#         for member in members_added:
#             if member.id != turn_context.activity.recipient.id:
#                 await turn_context.send_activity(
#                     MessageFactory.text("👋 Hello! I am your AI IT Assistant. How can I help you today?")
#                 )

#     async def on_message_activity(self, turn_context: TurnContext):
#         """Main Chat Loop with Multi-MCP Routing & Advanced State Management."""
#         user_input = turn_context.activity.text.strip()

#         # 1. Fetch User Info (With Emulator Fallback)
#         try:
#             member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
#             user_name = member.name or "Unknown User"
#             user_email = member.email or member.user_principal_name or "unknown@email.com"
#         except Exception:
#             user_name = turn_context.activity.from_property.name or "Local Tester"
#             user_email = "local_tester@domain.com"
        
#         self.conversation_references[user_email] = TurnContext.get_conversation_reference(turn_context.activity)
#         log_interaction(user_email, "user", user_input)

#         # 2. Retrieve Conversation History from Azure Blob
#         history = await self.history_accessor.get(turn_context, lambda:[])

#         # =======================================================
#         # 🚀 FIX 1: THE "START OVER" COMMAND (Context Confusion)
#         # =======================================================
#         # In ITSM, users switch topics (e.g., from Printer to Password).
#         # We give them a magic phrase to wipe the bot's memory manually.
#         if user_input.lower() in["start over", "clear", "new issue", "restart"]:
#             history =[]  # Wipe the array clean
#             await self.history_accessor.set(turn_context, history)
#             await turn_context.send_activity(MessageFactory.text("🔄 Conversation history cleared. What new issue can I help you with today?"))
#             return  # Stop processing here! Don't call OpenAI.

#         # 3. Inject Externalized Prompt on First Message
#         if not history:
#             compiled_system_prompt = self._load_system_prompt(user_name, user_email)
#             history.append({"role": "system", "content": compiled_system_prompt})

#         # Append the new user message
#         history.append({"role": "user", "content": user_input})

#         # =======================================================
#         # 🚀 FIX 2: THE "SLIDING WINDOW" (Token Bloat Protection)
#         # =======================================================
#         # Prevents OpenAI from crashing if the user chats 50+ times in a row.
#         MAX_TURNS = 15  # Keep the System Prompt + the last 14 messages
        
#         if len(history) > MAX_TURNS:
#             system_prompt = history[0]
            
#             # Slice the history to keep only the most recent messages
#             recent_history = history[-(MAX_TURNS - 1):]
            
#             # OpenAI Guardrail: NEVER orphan a 'tool' response. 
#             # If the oldest message in our slice is a 'tool' result, we must drop it 
#             # so OpenAI doesn't crash expecting the matching 'tool_call' request.
#             while recent_history and recent_history[0].get("role") == "tool":
#                 recent_history.pop(0)
                
#             history = [system_prompt] + recent_history
#         # =======================================================

#         # Send a typing indicator to Teams
#         await turn_context.send_activity(Activity(type=ActivityTypes.typing))
#         try:
#             # 🚀 PHASE 1: THE MULTI-SERVER ROUTER (AsyncExitStack) 🚀
#             async with AsyncExitStack() as stack:
                
#                 active_sessions = {}    # Maps: server_name -> ClientSession object
#                 tool_routing_map = {}   # Maps: tool_name -> server_name
#                 openai_tools =[]       # Master list of all tools for the LLM

#                 # 5. Dynamically connect to all ENABLED servers
#                 for server in self.mcp_config.get("mcp_servers",[]):
#                     if not server.get("enabled"):
#                         continue
                    
#                     server_name = server["name"]
#                     server_url = server["url"]

#                     try:
#                         print(f"🔌 Connecting to Microservice: {server_name} at {server_url}")
#                         read, write = await stack.enter_async_context(sse_client(server_url))
#                         session = await stack.enter_async_context(ClientSession(read, write))
#                         await session.initialize()
                        
#                         active_sessions[server_name] = session

#                         # Fetch tools from this specific server and build the Routing Map
#                         tools_response = await session.list_tools()
#                         for t in tools_response.tools:
#                             tool_routing_map[t.name] = server_name
#                             openai_tools.append({
#                                 "type": "function", 
#                                 "function": {
#                                     "name": t.name, 
#                                     "description": t.description, 
#                                     "parameters": t.inputSchema
#                                 }
#                             })
                            
#                     # 🚀 CRITICAL FIX: Catch Python 3.11+ TaskGroup ExceptionGroups!
#                     except ExceptionGroup as eg:
#                         print(f"❌ TaskGroup Error connecting to {server_name}: {eg}")
#                         await turn_context.send_activity(
#                             MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline. Some features may be unavailable.")
#                         )
#                     except Exception as e:
#                         print(f"❌ Failed to connect to {server_name}: {e}")
#                         await turn_context.send_activity(
#                             MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline. Some features may be unavailable.")
#                         )

#                 # Fail-safe if no tools loaded at all
#                 if not openai_tools:
#                     await turn_context.send_activity(MessageFactory.text("❌ All backend systems are offline. I cannot process your request right now. Please try again later."))
#                     return

#                 # --- 6. THE THINKING LOOP ---
#                 while True:
#                     response = await CLIENT.chat.completions.create(
#                         model=DEPLOYMENT, 
#                         messages=history, 
#                         tools=openai_tools, 
#                         tool_choice="auto"
#                     )
#                     msg = response.choices[0].message
#                     history.append(msg)
                    
#                     # CASE A: AI replies directly to the user
#                     if not msg.tool_calls:
#                         # 🟢 PHASE 5: Log the bot's final reply
#                         log_interaction(user_email, "bot", msg.content)
#                         await turn_context.send_activity(MessageFactory.text(msg.content))
#                         break
                    
#                     # CASE B: AI requests tool execution
#                     for tool in msg.tool_calls:
#                         tool_name = tool.function.name
#                         args = json.loads(tool.function.arguments)
                        
#                         target_server_name = tool_routing_map.get(tool_name)
                        
#                         if not target_server_name or target_server_name not in active_sessions:
#                             err_msg = f"System Error: Tool '{tool_name}' requested but routing to '{target_server_name}' failed."
#                             print(err_msg)
#                             history.append({"role": "tool", "tool_call_id": tool.id, "name": tool_name, "content": err_msg})
#                             continue

#                         # Granular UI Feedback
#                         friendly_name = tool_name.replace('_', ' ').title()
#                         await turn_context.send_activity(MessageFactory.text(f"⚙️ *{friendly_name}*..."))
                        
#                         # Execute the tool on the target server
#                         try:
#                             target_session = active_sessions[target_server_name]
#                             result = await target_session.call_tool(tool_name, arguments=args)
#                             tool_result_content = result.content[0].text
                            
#                             # 🟢 PHASE 5: Log the tool execution result
#                             log_interaction(user_email, "tool", tool_result_content, tool_name)
                            
#                         except Exception as tool_err:
#                             tool_result_content = f"Error executing tool: {str(tool_err)}"
#                             print(f"❌ Tool Error ({tool_name}): {tool_err}")
#                             log_interaction(user_email, "tool", tool_result_content, tool_name)
                        
#                         # Return the result back to the AI's context
#                         history.append({
#                             "role": "tool", 
#                             "tool_call_id": tool.id, 
#                             "name": tool_name, 
#                             "content": tool_result_content
#                         })
            
#             # 8. Save updated history to State
#             await self.history_accessor.set(turn_context, history)

#         except Exception as e:
#             print("❌ Critical Chat Error:")
#             traceback.print_exc()
#             await turn_context.send_activity(MessageFactory.text(f"⚠️ Critical Error processing your request: {str(e)}"))







import os
import json
import traceback
import base64 # 🚀 NEW: Required for image conversion
import aiohttp # 🚀 NEW: Required to download images
import msal
from contextlib import AsyncExitStack

from botbuilder.core import (
    ActivityHandler, 
    TurnContext, 
    MessageFactory, 
    ConversationState
)
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes
from botbuilder.core.teams import TeamsInfo
from botframework.connector.auth import MicrosoftAppCredentials # 🚀 NEW: Required to unlock Teams images

# Import Agent dependencies
from mcp import ClientSession
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv

# Import DB Logging
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
        if conversation_state is None:
            raise TypeError("[ITSMBot]: Missing parameter. conversation_state is required")

        self.conversation_state = conversation_state
        self.history_accessor = self.conversation_state.create_property("History")
        self.conversation_references = conversation_references

        self.config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_config.json"))
        try:
            with open(self.config_path, "r") as f:
                self.mcp_config = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ WARNING: {self.config_path} not found. Creating empty config in memory.")
            self.mcp_config = {"mcp_servers":[]}

    def _load_system_prompt(self, user_name: str, user_email: str) -> str:
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "prompts"))
        try:
            with open(os.path.join(base_dir, "base.txt"), "r", encoding="utf-8") as f:
                base_prompt = f.read().strip()
            with open(os.path.join(base_dir, "system.txt"), "r", encoding="utf-8") as f:
                system_prompt = f.read().strip()
            with open(os.path.join(base_dir, "business_rules.txt"), "r", encoding="utf-8") as f:
                business_rules = f.read().strip()
        except Exception as e:
            print(f"⚠️ Error loading prompts: {e}")
            return f"You are an IT Assistant. You are currently talking to {user_name} ({user_email})."

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

    # =======================================================
    # 🚀 PRODUCTION-READY: SECURE TEAMS IMAGE DOWNLOADER (MSAL)
    # =======================================================
    async def _download_teams_image(self, attachment_url: str, user_email: str) -> str:
        """Downloads an image from a secure MS Teams URL using MSAL for authentication."""
        try:
            app_id = os.getenv("MICROSOFT_APP_ID")
            app_password = os.getenv("MICROSOFT_APP_PASSWORD")
            tenant_id = os.getenv("MICROSOFT_APP_TENANT_ID")
            
            # 1. Use the official Microsoft Authentication Library (MSAL) for Single-Tenant
            authority = f"https://login.microsoftonline.com/{tenant_id}"
            
            # This MSAL class natively handles token caching for production performance
            msal_app = msal.ConfidentialClientApplication(
                client_id=app_id,
                client_credential=app_password,
                authority=authority
            )
            
            scopes = ["https://api.botframework.com/.default"]
            
            # First, try to get a cached token (Huge performance boost)
            result = msal_app.acquire_token_silent(scopes, account=None)
            
            if not result:
                # If no valid token is in the cache, request a new one from Azure
                result = msal_app.acquire_token_for_client(scopes=scopes)
                
            if "access_token" not in result:
                print(f"❌ MSAL Auth Error: {result.get('error_description')}")
                return None
                
            token = result["access_token"]
            
            # 2. Download the image bytes securely from Teams using the MSAL token
            headers = {"Authorization": f"Bearer {token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(attachment_url, headers=headers) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        # 🚀 NEW: Save image temporarily for the ServiceNow Tool to pick up
                        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "temp_images"))
                        os.makedirs(temp_dir, exist_ok=True) # Creates the folder if it doesn't exist
                        
                        # Sanitize email to use as a filename
                        safe_email = user_email.replace("@", "_").replace(".", "_")
                        temp_path = os.path.join(temp_dir, f"{safe_email}_latest.png")
                        
                        with open(temp_path, "wb") as f:
                            f.write(image_bytes)
                        # ---------------------------------------------------------

                        # 3. Convert to Base64 for OpenAI GPT-4o
                        return base64.b64encode(image_bytes).decode('utf-8')
                    else:
                        print(f"⚠️ Failed to download Teams image. HTTP Status: {response.status}")
        except Exception as e:
            print(f"❌ Error downloading attachment: {e}")
            
        return None

    async def on_turn(self, turn_context: TurnContext):
        await super().on_turn(turn_context)
        await self.conversation_state.save_changes(turn_context)

    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text("👋 Hello! I am your AI IT Assistant. You can describe your issue or paste a screenshot of the error!")
                )

    async def on_message_activity(self, turn_context: TurnContext):
        # 1. Get raw text (might be None if user ONLY sent an image)
        raw_text = turn_context.activity.text or ""
        user_input = raw_text.strip()
        attachments = turn_context.activity.attachments or[]

        try:
            member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
            user_name = member.name or "Unknown User"
            user_email = member.email or member.user_principal_name or "unknown@email.com"
        except Exception:
            user_name = turn_context.activity.from_property.name or "Local Tester"
            user_email = "local_tester@domain.com"
        
        self.conversation_references[user_email] = TurnContext.get_conversation_reference(turn_context.activity)

        history = await self.history_accessor.get(turn_context, lambda:[])

        if user_input.lower() in["start over", "clear", "new issue", "restart"]:
            history =[] 
            await self.history_accessor.set(turn_context, history)
            await turn_context.send_activity(MessageFactory.text("🔄 Conversation history cleared. What new issue can I help you with today?"))
            return  

        if not history:
            compiled_system_prompt = self._load_system_prompt(user_name, user_email)
            history.append({"role": "system", "content": compiled_system_prompt})

        # =======================================================
        # 🚀 NEW: MULTIMODAL MESSAGE FORMATTING
        # =======================================================
        message_content =[]
        
        # A. Add the text if the user typed something
        if user_input:
            message_content.append({"type": "text", "text": user_input})
            
        # B. Add the images if the user pasted screenshots
        for att in attachments:
            if "image" in att.content_type:
                await turn_context.send_activity(Activity(type=ActivityTypes.typing))
                base64_img = await self._download_teams_image(att.content_url, user_email)
                
                if base64_img:
                    message_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{att.content_type};base64,{base64_img}"}
                    })

        # C. Fallback if they sent an image with no text
        if not message_content:
            message_content.append({"type": "text", "text": "I have uploaded an image. Please analyze it."})
            user_input = "[User uploaded an image]"

        # Append the multimodal array to history instead of a simple string
        history.append({"role": "user", "content": message_content})
        
        # Log to DB (Text only for the admin dashboard)
        db_log_text = user_input + (" [Image Attached]" if attachments else "")
        log_interaction(user_email, "user", db_log_text)
        # =======================================================

        MAX_TURNS = 15  
        if len(history) > MAX_TURNS:
            system_prompt = history[0]
            recent_history = history[-(MAX_TURNS - 1):]
            while recent_history and recent_history[0].get("role") == "tool":
                recent_history.pop(0)
            history = [system_prompt] + recent_history

        await turn_context.send_activity(Activity(type=ActivityTypes.typing))
        try:
            async with AsyncExitStack() as stack:
                active_sessions = {}    
                tool_routing_map = {}   
                openai_tools =[]       

                for server in self.mcp_config.get("mcp_servers",[]):
                    if not server.get("enabled"):
                        continue
                    
                    server_name = server["name"]
                    server_url = server["url"]

                    try:
                        read, write = await stack.enter_async_context(sse_client(server_url))
                        session = await stack.enter_async_context(ClientSession(read, write))
                        await session.initialize()
                        
                        active_sessions[server_name] = session

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
                            
                    except ExceptionGroup as eg:
                        await turn_context.send_activity(MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline."))
                    except Exception as e:
                        await turn_context.send_activity(MessageFactory.text(f"⚠️ Backend service '{server_name}' is currently offline."))

                while True:
                    response = await CLIENT.chat.completions.create(
                        model=DEPLOYMENT, 
                        messages=history, 
                        tools=openai_tools if openai_tools else None, 
                        tool_choice="auto" if openai_tools else None
                    )
                    msg = response.choices[0].message
                    history.append(msg)
                    
                    # 🚀 PHASE 6: Extract live token usage
                    usage = response.usage
                    pt = usage.prompt_tokens if usage else 0
                    ct = usage.completion_tokens if usage else 0
                    tt = usage.total_tokens if usage else 0
                    
                    # CASE A: AI replies directly to the user
                    if not msg.tool_calls:
                        # 🟢 Log the bot's final reply
                        log_interaction(user_email, "bot", msg.content, prompt_tokens=pt, completion_tokens=ct, total_tokens=tt)
                        await turn_context.send_activity(MessageFactory.text(msg.content))
                        break
                    
                    # CASE B: AI requests tool execution
                    # Log the internal "thinking" step tokens so TPM/RPM is accurate
                    log_interaction(user_email, "bot_internal", f"Thinking: requested {len(msg.tool_calls)} tools", prompt_tokens=pt, completion_tokens=ct, total_tokens=tt)
                    
                    for tool in msg.tool_calls:
                        tool_name = tool.function.name
                        args = json.loads(tool.function.arguments)
                        target_server_name = tool_routing_map.get(tool_name)
                        
                        if not target_server_name or target_server_name not in active_sessions:
                            err_msg = f"System Error: Tool '{tool_name}' failed routing."
                            history.append({"role": "tool", "tool_call_id": tool.id, "name": tool_name, "content": err_msg})
                            continue

                        friendly_name = tool_name.replace('_', ' ').title()
                        await turn_context.send_activity(MessageFactory.text(f"⚙️ *{friendly_name}*..."))
                        
                        try:
                            target_session = active_sessions[target_server_name]
                            result = await target_session.call_tool(tool_name, arguments=args)
                            tool_result_content = result.content[0].text
                            log_interaction(user_email, "tool", tool_result_content, tool_name)
                        except Exception as tool_err:
                            tool_result_content = f"Error executing tool: {str(tool_err)}"
                            log_interaction(user_email, "tool", tool_result_content, tool_name)
                        
                        history.append({
                            "role": "tool", 
                            "tool_call_id": tool.id, 
                            "name": tool_name, 
                            "content": tool_result_content
                        })
            
            await self.history_accessor.set(turn_context, history)

        except Exception as e:
            traceback.print_exc()
            await turn_context.send_activity(MessageFactory.text(f"⚠️ Critical Error processing your request: {str(e)}"))