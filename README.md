
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
```

### 4. Generate Mock Data
Run this script once to create the `data/` folder and Excel files.
```bash
python setup_data.py
```

---

## ⚡ How to Run (The 3-Terminal Setup)

You need to run three separate processes to simulate the distributed system.

### Terminal 1: The MCP Server (Tools Host)
This provides the "API" that the agents use.
```bash
python -m mcp_server.server
```
*Wait until you see: `🚀 MCP Server Running...`*

### Terminal 2: The Chat Agent (Front Desk)
This is where you act as the User.
```bash
python -m agent.chat_agent
```

### Terminal 3: The Worker Agent (Back Office)
This runs the background loop.
```bash
python -m agent.worker_agent
```

---

## 🧪 Test Scenarios

Use these inputs in the **Chat Agent (Terminal 2)** and watch what happens in the **Worker Agent (Terminal 3)**.

### Scenario A: The Critical SAP Issue (High Priority)
*   **User Input:** "My SAP login is failing with error 500."
*   **Chat Agent Action:** 
    *   Detects "SAP" & "Error 500". 
    *   Azure Search returns **P1 Critical** policy.
    *   Creates Ticket (e.g., `INC1001`).
*   **Worker Agent Action:**
    *   Wakes up.
    *   Reads `INC1001`.
    *   Maps "SAP" $\to$ `SAP_Support` Team.
    *   Checks Roster:
        *   Alice (High Load)
        *   **Bob (Low Load)** $\leftarrow$ Selected.
    *   **Result:** Assigns ticket to **Bob**.

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
*   The worker sleeps for 15 seconds between loops. Be patient, or check if the ticket status in `servicenow_mock_db.json` is actually "New".

