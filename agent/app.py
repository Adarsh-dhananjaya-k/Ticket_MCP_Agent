


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

# Import the bot logic
from agent.teams_bot import ITSMBot

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

CONVERSATION_REFERENCES = dict()

# We pass the conversation_state to the bot so it can save/read history.
BOT = ITSMBot(CONVERSATION_STATE, CONVERSATION_REFERENCES)

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
    
# --- NEW: PROACTIVE NOTIFICATION WEBHOOK ---
async def notify(req: web.Request) -> web.Response:
    """ServiceNow will POST to this URL when a ticket is resolved."""
    try:
        body = await req.json()
        target_email = body.get("user_email")
        message_text = body.get("message")

        # Find the active chat for this user
        conversation_reference = CONVERSATION_REFERENCES.get(target_email)

        if not conversation_reference:
            print(f"⚠️ No active chat found in memory for {target_email}")
            return web.Response(status=404, text=f"No active chat found for {target_email}")

        # Helper to send the message into Teams
        async def send_proactive_message(turn_context):
            await turn_context.send_activity(message_text)

        # Tell the Bot Adapter to push the message!
        await ADAPTER.continue_conversation(
            conversation_reference, 
            send_proactive_message, 
            APP_ID
        )
        return web.Response(status=200, text="Notification Sent!")
        
    except Exception as e:
        print(f"❌ Notification Error: {e}")
        return web.Response(status=500, text=str(e))

# --- 6. INITIALIZE WEB APP ---
# (This was missing in the previous version)
app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_post("/api/notify", notify)

if __name__ == "__main__":
    try:
        print(f"🚀 Teams Bot running on http://localhost:3978")
        web.run_app(app, host="localhost", port=3978)
    except Exception as error:
        raise error
