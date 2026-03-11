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
from mcp_server.tools.servicenow import update_incident, get_tickets
from mcp_server.tools.roster import find_best_assignee
from mcp_server.tools import approval_tracker

load_dotenv()

# --- 1. LOAD CREDENTIALS ---
APP_ID = os.getenv("MICROSOFT_APP_ID")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
TENANT_ID = os.getenv("MICROSOFT_APP_TENANT_ID")

if not all([APP_ID, APP_PASSWORD, TENANT_ID]):
    print("⚠️ WARNING: Missing Azure Bot credentials in .env")
    print("Teams Chat functionality will be disabled, but Manager Approval links will still work.")
    # We set these to dummies so the adapter doesn't crash on init
    APP_ID = APP_ID or "dummy"
    APP_PASSWORD = APP_PASSWORD or "dummy"
    TENANT_ID = TENANT_ID or "dummy"
else:
    print("✅ Azure Bot credentials loaded.")

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
    assignment_group = req.query.get("assignment_group")
    
    if not ticket_id:
        return web.Response(text="Missing ticket_id", status=400)
    
    assignee_data = None
    if not agent_email or agent_email == "":
        print(f"🔍 Agent Email missing for {ticket_id}. System is handling it...")
        tickets = get_tickets({"number": ticket_id})
        if isinstance(tickets, list) and len(tickets) > 0:
            desc = tickets[0].get("desc", "")
            assignee_data = find_best_assignee(desc)
            agent_email = assignee_data.get("agent_email")
            assignment_group = assignment_group or assignee_data.get("assignment_group")
            print(f"✅ Found best agent automatically: {agent_email}")
        else:
            return web.Response(text=f"Error: Could not find ticket {ticket_id} to auto-assign.", status=404)

    if not assignment_group and not assignee_data:
        tickets = get_tickets({"number": ticket_id})
        if isinstance(tickets, list) and len(tickets) > 0:
            desc = tickets[0].get("desc", "")
            derived = find_best_assignee(desc)
            assignment_group = derived.get("assignment_group")

    if not agent_email:
        return web.Response(text="Could not determine agent for assignment.", status=400)
    
    print(f"✅ Manager Approved Ticket {ticket_id}. Assigning to {agent_email}")
    
    result = update_incident(
        ticket_id,
        assigned_to=agent_email,
        assignment_group=assignment_group,
        status="in progress",
        comments="Manager approved via email link."
    )
    approval_tracker.clear(ticket_id)
    
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
    approval_tracker.clear(ticket_id)
    
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
