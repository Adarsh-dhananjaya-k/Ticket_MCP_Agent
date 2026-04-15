import sys
import os
import json
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

# Import the bot logic and DB
from agent.teams_bot import ITSMBot
from agent.db import init_db, get_recent_logs, get_admin_stats, get_sessions
from agent.blob_storage import EntraIdBlobStorage

load_dotenv()

# 🚀 INIT DB
init_db()

# --- 1. LOAD CREDENTIALS ---
APP_ID = os.getenv("MICROSOFT_APP_ID")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD")
TENANT_ID = os.getenv("MICROSOFT_APP_TENANT_ID")

if not all([APP_ID, APP_PASSWORD, TENANT_ID]):
    print("❌ Missing Azure Bot credentials")
    sys.exit(1)

# --- 2. SETUP ADAPTER ---
SETTINGS = BotFrameworkAdapterSettings(
    app_id=APP_ID, 
    app_password=APP_PASSWORD,
    channel_auth_tenant=TENANT_ID 
)

ADAPTER = BotFrameworkAdapter(SETTINGS)

# --- 3. BOT STATE (AZURE BLOB) ---
STORAGE_URL = os.getenv("AZURE_STORAGE_ACCOUNT_URL")
CONTAINER_NAME = os.getenv("BLOB_CONTAINER_NAME", "bot-state")

if STORAGE_URL:
    print(f"✅ Using Azure Blob Storage for state: {STORAGE_URL}")
    STORAGE = EntraIdBlobStorage(account_url=STORAGE_URL, container_name=CONTAINER_NAME)
else:
    print("⚠️ WARNING: Falling back to Memory Storage! Active chats will be lost on restart.")
    STORAGE = MemoryStorage()

CONVERSATION_STATE = ConversationState(STORAGE)

# --- 4. BOT ---
CONVERSATION_REFERENCES = dict()
BOT = ITSMBot(CONVERSATION_STATE, CONVERSATION_REFERENCES)

# =========================================================
# 🚨 CRITICAL FIX: GLOBAL MIDDLEWARE FOR TEAMS IFRAME
# =========================================================

@web.middleware
async def teams_iframe_middleware(request, handler):
    response = await handler(request)

    # 🚀 FIX FOR ERR_INVALID_RESPONSE:
    # Only inject iframe headers into the HTML page. 
    # Injecting headers into static FileResponses (.js, .css) corrupts the stream!
    if response.content_type == "text/html":
        response.headers["Content-Security-Policy"] = (
            "frame-ancestors 'self' https://teams.microsoft.com https://*.teams.microsoft.com https://*.skype.com https://teams.cloud.microsoft https://*.cloud.microsoft;"
        )
        response.headers.pop("X-Frame-Options", None)

    return response

# --- 5. BOT ENDPOINT ---
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
        print(f"❌ Error: {exception}")
        traceback.print_exc()
        return web.Response(status=500)

# --- 6. PROACTIVE NOTIFICATION ---
async def notify(req: web.Request) -> web.Response:
    try:
        body = await req.json()
        target_email = body.get("user_email")
        message_text = body.get("message")

        conversation_reference = CONVERSATION_REFERENCES.get(target_email)

        if not conversation_reference:
            return web.Response(status=404, text="No active chat found")

        async def send_proactive_message(turn_context):
            await turn_context.send_activity(message_text)

        await ADAPTER.continue_conversation(
            conversation_reference, 
            send_proactive_message, 
            APP_ID
        )

        return web.Response(status=200, text="Notification Sent!")

    except Exception as e:
        return web.Response(status=500, text=str(e))

# =========================================================
# 🚀 ADMIN DASHBOARD
# =========================================================
# 1. Get the folder app.py is in (the 'agent' folder)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Go UP one level to the root 'TICKET_MCP_AGENT' folder
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# 3. Now point to admin-ui
REACT_DIST_DIR = os.path.join(ROOT_DIR, "admin-ui", "dist")

async def serve_react_app(req: web.Request) -> web.Response:
    try:
        index_path = os.path.join(REACT_DIST_DIR, "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html")
    except Exception as e:
        return web.Response(status=404, text=f"React build not found. Path checked: {index_path}. Error: {str(e)}")
    
async def api_get_logs(req: web.Request) -> web.Response:
    logs = get_recent_logs(100)
    return web.json_response(logs)

async def api_get_stats(req: web.Request) -> web.Response:
    stats = get_admin_stats()
    return web.json_response(stats)

async def api_get_sessions(req: web.Request) -> web.Response:
    query = req.rel_url.query.get("q")
    limit_param = req.rel_url.query.get("limit")
    try:
        limit = int(limit_param) if limit_param else 1000
    except ValueError:
        limit = 1000
    sessions = get_sessions(limit=limit, query=query)
    return web.json_response({"sessions": sessions})

async def api_get_config(req: web.Request) -> web.Response:
    try:
        with open("mcp_config.json", "r") as f:
            return web.json_response(json.load(f))
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def api_update_config(req: web.Request) -> web.Response:
    try:
        data = await req.json()

        with open("mcp_config.json", "w") as f:
            json.dump(data, f, indent=4)

        BOT.mcp_config = data
        return web.json_response({"status": "success"})

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

# =========================================================
# --- APP INIT
# =========================================================

app = web.Application(middlewares=[teams_iframe_middleware])

app.router.add_post("/api/messages", messages)
app.router.add_post("/api/notify", notify)

# --- 🟢 REACT FRONTEND ROUTES 🟢 ---
app.router.add_get("/admin", serve_react_app)

# 🚀 THE FIX: Use absolute OS paths to serve the assets folder safely
assets_path = os.path.join(REACT_DIST_DIR, "assets")
if os.path.exists(assets_path):
    app.router.add_static("/assets", path=assets_path, name="assets")
else:
    print(f"⚠️ WARNING: React assets folder not found at {assets_path}. Did you run 'npm run build'?")

# --- BACKEND API ROUTES ---
app.router.add_get("/api/admin/logs", api_get_logs)
app.router.add_get("/api/admin/stats", api_get_stats)
app.router.add_get("/api/admin/sessions", api_get_sessions)
app.router.add_get("/api/admin/config", api_get_config)
app.router.add_post("/api/admin/config", api_update_config)

# =========================================================

if __name__ == "__main__":
    print("🚀 Running on http://localhost:3978")
    web.run_app(app, host="0.0.0.0", port=3978)
