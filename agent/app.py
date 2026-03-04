# import sys
# import os
# import traceback
# from aiohttp import web
# from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings
# from botbuilder.schema import Activity
# from dotenv import load_dotenv

# # Import the bot logic
# from agent.teams_bot import ITSMBot

# load_dotenv()

# # --- 1. LOAD CREDENTIALS ---
# APP_ID = os.getenv("MICROSOFT_APP_ID")
# APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
# TENANT_ID = os.getenv("MICROSOFT_APP_TENANT_ID")

# if not all([APP_ID, APP_PASSWORD, TENANT_ID]):
#     print("❌ ERROR: Missing Azure Bot credentials in .env")
#     print("Ensure MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, and MICROSOFT_APP_TENANT_ID are set.")
#     sys.exit(1)

# # --- 2. SETUP ADAPTER (SINGLE TENANT CONFIG) ---
# # We must pass 'channel_auth_tenant' to tell Azure WHICH directory to check.
# SETTINGS = BotFrameworkAdapterSettings(
#     app_id=APP_ID, 
#     app_password=APP_PASSWORD,
#     channel_auth_tenant=TENANT_ID 
# )

# ADAPTER = BotFrameworkAdapter(SETTINGS)

# # --- 3. INITIALIZE BOT ---
# BOT = ITSMBot()

# # --- 4. WEBHOOK HANDLER ---
# async def messages(req: web.Request) -> web.Response:
#     if "application/json" in req.headers.get("Content-Type", ""):
#         body = await req.json()
#     else:
#         return web.Response(status=415)

#     activity = Activity().deserialize(body)
#     auth_header = req.headers.get("Authorization", "")

#     try:
#         await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
#         return web.Response(status=201)
#     except Exception as exception:
#         print(f"❌ Error processing request: {exception}")
#         traceback.print_exc()
#         return web.Response(status=500)

# # --- 5. RUN SERVER ---
# app = web.Application()
# app.router.add_post("/api/messages", messages)

# if __name__ == "__main__":
#     try:
#         print(f"🚀 Teams Bot (Single Tenant) running on http://localhost:3978")
#         web.run_app(app, host="localhost", port=3978)
#     except Exception as error:
#         raise error


import sys
import os
import traceback
from aiohttp import web
from botbuilder.core import (
    BotFrameworkAdapter, 
    BotFrameworkAdapterSettings, 
    MemoryStorage, 
    ConversationState
)
from botbuilder.schema import Activity
from dotenv import load_dotenv

# Import the bot logic and ServiceNow tools
from agent.teams_bot import ITSMBot
from mcp_server.tools.servicenow import update_incident

load_dotenv()

# --- 1. LOAD CREDENTIALS ---
APP_ID = os.getenv("MICROSOFT_APP_ID")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
TENANT_ID = os.getenv("MICROSOFT_APP_TENANT_ID")

if not all([APP_ID, APP_PASSWORD, TENANT_ID]):
    print("❌ ERROR: Missing Azure Bot credentials in .env")
    print("Ensure MICROSOFT_APP_ID, MICROSOFT_APP_PASSWORD, and MICROSOFT_APP_TENANT_ID are set.")
    sys.exit(1)

# --- 2. SETUP ADAPTER ---
SETTINGS = BotFrameworkAdapterSettings(
    app_id=APP_ID, 
    app_password=APP_PASSWORD,
    channel_auth_tenant=TENANT_ID 
)

ADAPTER = BotFrameworkAdapter(SETTINGS)

# --- 3. SETUP MEMORY (CONTEXT) ---
# MemoryStorage keeps data in RAM. Restarting the app clears the memory.
MEMORY = MemoryStorage()
CONVERSATION_STATE = ConversationState(MEMORY)

# --- 4. INITIALIZE BOT WITH STATE ---
# We pass the conversation_state to the bot so it can save/read history.
BOT = ITSMBot(CONVERSATION_STATE)

# --- 5. WEBHOOK HANDLER ---
async def messages(req: web.Request) -> web.Response:
    if "application/json" in req.headers.get("Content-Type", ""):
        body = await req.json()
    else:
        return web.Response(status=415)

    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")

    try:
        await ADAPTER.process_activity(activity, auth_header, BOT.on_turn)
        return web.Response(status=201)
    except Exception as exception:
        print(f"❌ Error processing request: {exception}")
        traceback.print_exc()
        return web.Response(status=500)

# --- 6. APPROVAL HANDLERS ---
async def approve_ticket(req: web.Request) -> web.Response:
    ticket_id = req.query.get("ticket_id")
    agent_email = req.query.get("agent_email")
    
    if not ticket_id or not agent_email:
        return web.Response(text="Missing ticket_id or agent_email", status=400)
    
    print(f"✅ Manager Approved Ticket {ticket_id}. Assigning to {agent_email}")
    
    # Direct update to ServiceNow
    result = update_incident(ticket_id, assigned_to=agent_email, status="Assigned", comments="Manager approved via email link.")
    
    return web.Response(
        text=f"<h1>Ticket Approved</h1><p>{result}</p><p>Ticket {ticket_id} has been assigned to {agent_email}.</p>",
        content_type="text/html"
    )

async def reject_ticket(req: web.Request) -> web.Response:
    ticket_id = req.query.get("ticket_id")
    
    if not ticket_id:
        return web.Response(text="Missing ticket_id", status=400)
    
    print(f"❌ Manager Rejected Ticket {ticket_id}")
    
    # Direct update to ServiceNow
    result = update_incident(ticket_id, status="On Hold", comments="Manager rejected assignment.")
    
    return web.Response(
        text=f"<h1>Ticket Rejected</h1><p>{result}</p><p>Ticket {ticket_id} has been put on hold.</p>",
        content_type="text/html"
    )

# --- 6. INITIALIZE WEB APP ---
# (This was missing in the previous version)
app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_get("/approve", approve_ticket)
app.router.add_get("/reject", reject_ticket)

if __name__ == "__main__":
    try:
        print(f"🚀 Teams Bot running on http://localhost:3978")
        web.run_app(app, host="localhost", port=3978)
    except Exception as error:
        raise error