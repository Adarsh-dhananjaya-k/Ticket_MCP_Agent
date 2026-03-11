
# 🤖 Agentic ITSM System (Dual-Agent Architecture)

A Multi-Agent System (MAS) for IT Service Management using the **Model Context Protocol (MCP)** and **Azure OpenAI**.

This system demonstrates a "Human-in-the-Loop" architecture with two distinct AI Agents working in parallel:
1.  **Chat Agent (Front Desk):** Handles real-time user intake, SLA lookups via Azure AI Search, and ticket creation.
2.  **Worker Agent (Back Office):** Runs autonomously to detect new tickets, analyze workloads via Excel Rosters, and assign tickets to the best available engineer.



---

## 📂 Project Structure

```text
📦Ticket_MCP_Agent
 ┣ 📂agent
 ┃ ┣ 📜chat_agent.py
 ┃ ┣ 📜worker_agent.py
 ┃ ┗ 📜__init__.py
 ┣ 📂data
 ┃ ┣ 📜roster.xlsx
 ┃ ┗ 📜teams_mapping.xlsx
 ┣ 📂mcp_server
 ┃ ┣ 📂tools
 ┃ ┃ ┣ 📜roster.py
 ┃ ┃ ┣ 📜servicenow.py
 ┃ ┃ ┣ 📜sla_policy.py
 ┃ ┃ ┣ 📜email_service.py
 ┃ ┃ ┗ 📜__init__.py
 ┃ ┣ 📜server.py
 ┃ ┗ 📜__init__.py
 ┣ 📜.env
 ┣ 📜.gitignore
 ┣ 📜README.md
 ┣ 📜requirements.txt
 ┗ 📜setup_data.py
```

---

## 🚀 Installation & Setup

### 1. Prerequisites
*   Python 3.10+
*   Azure OpenAI Endpoint & Key
*   Azure AI Search Endpoint & Key (with a "sla-index" created)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Create a `.env` file in the root directory:
```ini
# Azure OpenAI
AZURE_OPENAI_ENDPOINT="https://YOUR-RESOURCE.openai.azure.com/"
AZURE_OPENAI_KEY="your-key-here"
AZURE_OPENAI_API_VERSION="2024-08-01-preview"
AZURE_OPENAI_DEPLOYMENT="gpt-4o"

# Azure AI Search (Knowledge Base)
AZURE_SEARCH_ENDPOINT="https://YOUR-SEARCH.search.windows.net"
AZURE_SEARCH_KEY="your-admin-key"
AZURE_SEARCH_INDEX_NAME="sla-index"

# ServiceNow (ITSM System)
SNOW_INSTANCE="devXXXXX.service-now.com"
SNOW_USER="your-username"
SNOW_PASSWORD="your-password"

# SMTP (Email Service) — REQUIRED for P1 approvals
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your-email@gmail.com"
SMTP_PASSWORD="your-app-password"
SMTP_FROM_EMAIL="your-email@gmail.com"
BASE_URL="http://localhost:3978" 
```

> **Important:** Leave these SMTP values blank and every P1 ticket will be left in `Pending` because the worker cannot send the manager approval email. Use a real mailbox/app password before testing the approval loop.

You can quickly verify the SMTP configuration with:
```bash
python scripts/check_smtp_service.py --to your-email@example.com
```
The script attempts to log in and send a test message so you can catch credential issues before launching the system.

### 4. Verify ServiceNow Connection (Optional)
You can run a quick check to see if your ServiceNow credentials are correct:
```bash
python -m scripts.verify_sn_config
```

### 4. Generate Mock Data
Run this script once to create the `data/` folder and Excel files.
```bash
python setup_data.py
```

The generated `data/roster.xlsx` now contains `Assignment_Group`, `Team`, `Manager`, workload, and role columns. The worker agents and approval flow read that `Assignment_Group` value so ServiceNow receives both the assignee and the correct assignment group.

### 5. Sync Roster from ServiceNow (optional but recommended)
If your ServiceNow instance already contains the right users/groups, mirror them back into Excel so assignments stay accurate:
```bash
python scripts/sync_snow_roster.py
```
This populates each roster row with `Assignment_Group` and manager data pulled live via the ServiceNow API.

---

## ⚡ How to Run

You can now run the entire system with a single command using the master startup script.

### Option 1: The Master Startup Script (Recommended)
Launch the MCP Server, the Teams Bot, and the Worker Agent in parallel.
```bash
python run_system.py
```

### Option 2: Manual 3-Terminal Setup
If you prefer separate logs:

1. **Terminal 1: MCP Server** -> `python -m mcp_server.server`
2. **Terminal 2: Teams Bot** -> `python -m agent.app`
3. **Terminal 3: Worker Agent** -> `python -m agent.worker_agent`

---

---

## 🤝 Human-in-the-Loop: Manager Approval Workflow

The system incorporates a mandatory approval step for **Critical (P1)** tickets before they are assigned to team members.

1.  **Detection**: The Worker Agent identifies a P1 ticket.
2.  **Notification**: An approval request is sent via SMTP to the specific **Team Manager** (defined in `data/teams_mapping.xlsx`).
3.  **Action**: The Manager receives an HTML email with two buttons:
    *   **APPROVE**: Automatically assigns the ticket to the best agent in ServiceNow.
    *   **REJECT**: Puts the ticket on hold and adds a rejection comment.
4.  **Audit**: All actions are recorded directly in the ServiceNow ticket work notes.

---

## 🧪 Test Scenarios

Use these inputs in the **Chat Agent (Terminal 2)** and watch what happens in the **Worker Agent (Terminal 3)**.

### Scenario A: The Critical SAP Issue (High Priority Approval)
*   **User Input:** "My SAP login is failing with error 500."
*   **Worker Agent Action:**
    *   Detects Priority 1.
    *   Maps "SAP" $\to$ `SAP_Support` Team.
    *   Sends **Approval Email** to `softmgr@demo.com` instead of immediate assignment.
*   **Manager Action:**
    *   Manager clicks **APPROVE** in their email.
    *   Ticket status updates to `Assigned` and `assigned_to` is set to the best agent (e.g., Bob).

### Scenario B: Database Access (Medium Priority)
*   **User Input:** "I need read access to the Oracle SQL database."
*   **Chat Agent Action:**
    *   Detects "Oracle" / "Access".
    *   Azure Search returns **P2/P3** policy.
    *   Creates Ticket (e.g., `INC1002`).
*   **Worker Agent Action:**
    *   Maps "Oracle" $\to$ `Database_Admin` Team.
    *   Checks Roster:
        *   **Charlie (Medium Load)** $\leftarrow$ Selected.
    *   **Result:** Assigns ticket to **Charlie**.

### Scenario C: WiFi/Network (Low Priority)
*   **User Input:** "The office WiFi is a bit slow today."
*   **Chat Agent Action:**
    *   Detects "WiFi" / "Slow".
    *   Creates Ticket.
*   **Worker Agent Action:**
    *   Maps "WiFi" $\to$ `Network_Ops` Team.
    *   Checks Roster.
    *   **Result:** Assigns to **David**.

---

## 🛠️ Troubleshooting

**1. `openai.NotFoundError: Error code: 404`**
*   Check your `.env` file. The `AZURE_OPENAI_DEPLOYMENT` must match the **Deployment Name** in Azure AI Studio, not the model name.

**2. `ConnectionRefusedError`**
*   Make sure **Terminal 1 (Server)** is running before you start the agents.

**3. Worker isn't picking up tickets**
*   The worker sleeps for 15 seconds between loops. Ensure the ticket state in ServiceNow is "New" (State Code 1) and that it is "Unassigned".

**4. Ticket shows “Assigned” in logs but not in ServiceNow**
*   ServiceNow refuses to populate `assigned_to` unless `assignment_group` is set. Make sure your roster rows include the exact group name (see `setup_data.py` output or rerun `scripts/sync_snow_roster.py`). The MCP layer forwards that group automatically with each `assign_ticket`/`request_manager_approval` call.

**5. “Failed to send approval email … Check SMTP configuration.”**
*   One or more SMTP values in `.env` are blank or incorrect. Until you provide a working mailbox/app password, P1 tickets are moved to `Pending` and require manual assignment.

