



# 🤖 AI-Powered IT Service Desk Bot for Microsoft Teams

An intelligent, conversational IT Service Desk assistant built for Microsoft Teams. This bot leverages **Azure OpenAI**, **Azure AI Search (RAG)**, the **Model Context Protocol (MCP)**, and **ServiceNow** to automate incident routing, triage, and manager approvals.

## ✨ Key Features
* **Conversational Interface:** Users report IT issues natively within Microsoft Teams.
* **Automated SLA & Priority Triage:** Uses Azure AI Search to query internal SLA policy documents to dynamically determine the Priority/Urgency of a ticket.
* **Smart AI Assignment Routing:** Queries an Excel-based team mapping matrix and cross-references it with **real-time ServiceNow workload metrics** to find the absolute best available L1/L2 agent.
* **ServiceNow Integration:** Automatically creates, updates, and resolves incidents in ServiceNow.
* **1-Click Secure Manager Approvals:** For high-priority (P1) issues, the bot places the ticket "On Hold", generates a cryptographically secure token, and emails the manager. The manager can approve the AI's suggested assignment with a single click from their phone/laptop—**without needing to log in to ServiceNow.**

---

## 🏗️ Architecture
1. **Microsoft Teams / Bot Framework (`app.py`):** Maintains conversational state and user interaction.
2. **AI Reasoning Engine (`teams_bot.py`):** Azure OpenAI processes the conversation, determines the next steps, and decides which tools to call.
3. **MCP Tool Server (`server.py`):** Exposes Python functions as discrete tools for the AI to use (e.g., `create_ticket`, `find_assignee`, `lookup_sla_policy`).
4. **ServiceNow Custom APIs:** Handles secure token storage, approval record generation, and unauthenticated one-click email actions.

---

## 📋 Prerequisites
* **Python 3.9+**
* **Microsoft Azure Account:** Azure OpenAI deployment & Azure AI Search index (with your SLA policies loaded).
* **Microsoft Bot Framework:** App ID and Password for Teams integration.
* **ServiceNow Developer Instance:** Admin access to create custom fields and APIs.

---

## ⚙️ Environment Variables Setup
Create a `.env` file in the root directory of the project and populate it with the following:

```env
# Microsoft Bot Framework Credentials
MICROSOFT_APP_ID=your_bot_app_id
MICROSOFT_APP_PASSWORD=your_bot_password
MICROSOFT_APP_TENANT_ID=your_tenant_id

# Azure OpenAI Credentials
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your_openai_key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT=your_model_deployment_name

# Azure AI Search (SLA Policy Knowledge Base)
AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_SEARCH_KEY=your_search_key
AZURE_SEARCH_INDEX_NAME=your_index_name

# ServiceNow Credentials
SNOW_INSTANCE=devXXXXX.service-now.com
SNOW_USER=admin
SNOW_PASSWORD=your_snow_password
```

---

## 🛠️ ServiceNow Configuration
To make the 1-click token approval system work, you must configure the following in your ServiceNow instance:

### 1. Custom Fields
* Navigate to the `incident` table and add a new custom field of type **Reference** (pointing to the `sys_user` table) named `u_ai_suggested_engineer`.
* Ensure the out-of-the-box `correlation_id` field is active on the incident table (used to store the secure one-time token).

### 2. Custom Scripted REST API
Navigate to **Scripted REST APIs** and create a new API:
* **Name:** Teams Bot API
* **API ID:** `teams_bot_api` (Namespace: e.g., `1920142`)

**Resource A: Create Approval (POST)**
* **Relative Path:** `/create_approval`
* **Requires Authentication:** Yes
* **Purpose:** Takes the payload from Python, saves the secure token to the incident's `correlation_id`, and creates the `sysapproval_approver` record.

**Resource B: Process Approval Click (GET)**
* **Relative Path:** `/process_approval`
* **Requires Authentication:** ❌ **NO** (Uncheck this box so managers can click the email without logging in).
* **Purpose:** Reads the `token` parameter from the URL, validates it against the incident's `correlation_id`, assigns the ticket, clears the token, and returns a success HTML page.

### 3. Email Notification & Script
* Navigate to **System Notification -> Email -> Notification Email Scripts**.
* Create a script named `generate_manager_assignment_links`.
* This script loops through the assignment group members, grabs the secret token from the incident, and generates the dynamic HTML buttons for the manager's email.

---

## 🚀 Installation & Running the Application

**1. Clone the repository and install dependencies:**
```bash
git clone https://github.com/yourusername/teams-itsm-bot.git
cd teams-itsm-bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**2. Ensure local data files are present:**
Ensure `roster.xlsx` and `teams_mapping.xlsx` exist in the `data/` folder.

**3. Start the MCP Server:**
Open a terminal and start the tool server (runs on port 8000 via SSE).
```bash
python server.py
```

**4. Start the Teams Bot:**
Open a second terminal and start the aiohttp web server.
```bash
python app.py
```

**5. Expose to the Internet (For Local Testing):**
If testing locally with Microsoft Teams or the Bot Framework Emulator, use Ngrok to tunnel port 3978.
```bash
ngrok http 3978
```
*(Update your Azure Bot Messaging Endpoint to `https://<your-ngrok-url>.ngrok.app/api/messages`)*

---

## 🧪 How to Use (Workflow Example)
1. **User:** "Hi, my design software keeps crashing on startup. Please help."
2. **Bot (Thinking):**
   * Calls `lookup_sla_policy` -> Determines this is an urgent/Critical P1 issue.
   * Calls `find_assignee` -> Looks at Excel mappings, determines it belongs to `Software_Support`. Queries SNOW to find that "Karen" has 0 active tickets.
   * Calls `create_ticket` -> Creates INC0010147.
   * Calls `request_manager_approval` -> Puts ticket On Hold, generates token, pushes to SNOW.
3. **Bot (Response):** "I have created INC0010147. Because this is a Critical Priority issue, it has been placed On Hold while an email is sent to your team manager to approve the AI-suggested assignment to Karen."
4. **Manager:** Receives the email, clicks **"⭐ Approve AI Assignment[Karen]"**.
5. **System:** Token is validated instantly. Ticket is assigned to Karen and moved to "In Progress".

---

## 🛡️ Security Notes
* The unauthenticated `/process_approval` API endpoint is secured by cryptographically strong, 32-character pseudo-random URL-safe tokens.
* Tokens are strictly single-use. Once clicked, the `correlation_id` is cleared from ServiceNow, rendering the URL permanently inactive.