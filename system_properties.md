


This is exactly how you mature an application. Let’s tackle both of these items to get your architecture closer to a true Enterprise standard.

---

### Phase 1: ServiceNow System Properties (Removing Hardcoded URLs)

Hardcoding your Ngrok URL (`https://interfaith-rubi-westerly.ngrok-free.dev`) in a Business Rule means that every time your Ngrok URL changes (or if you move to a production server), you have to modify the code. 

Here is the "ServiceNow Way" to fix this using **System Properties**.

#### Step 1: Create the System Property
1. In ServiceNow, type `sys_properties.list` in the left navigation filter and press Enter.
2. Click **New**.
3. Fill in the details:
   * **Name:** `teams_bot.notify_url`
   * **Type:** `string`
   * **Value:** `https://interfaith-rubi-westerly.ngrok-free.dev/api/notify`
4. Click **Submit**.

#### Step 2: Update the Business Rule Script
Now, update your **"Notify Teams on Resolve"** Business Rule to pull that property dynamically. 

Change this section of your existing script:
```javascript
// ⚠️ OLD HARDCODED WAY
// request.setEndpoint('https://interfaith-rubi-westerly.ngrok-free.dev/api/notify'); 

// ✅ NEW DYNAMIC WAY
var notifyUrl = gs.getProperty('teams_bot.notify_url');
if (!notifyUrl) {
    gs.error("Teams Notify: 'teams_bot.notify_url' system property is missing!");
    return;
}
request.setEndpoint(notifyUrl);
```
Now, whenever your Ngrok URL changes, you just update the System Property. Zero code changes required!

---

### Phase 2: Upgrading the Admin Dashboard to React

Yes, moving from a single `admin.html` file to **React** is the standard for production Teams apps. 

**Why is it better?**
* **State Management:** React handles live-updating tables (like your logs) and toggle switches much smoother without messy DOM manipulation.
* **Component-Based:** You can separate the "Logs View" and the "Server Config View" into different files.
* **Microsoft Fluent UI:** Later, you can easily install `@fluentui/react-components` to make your dashboard look *exactly* like native Microsoft Teams.

Because you are using **one Ngrok URL** for everything, the most efficient architecture is to **build the React app into static files, and have your Python (`aiohttp`) server host them.** This avoids CORS issues entirely.

Here is the step-by-step production way to do this using **Vite** (the modern standard for React).

#### Step 1: Initialize the React App
Open your terminal in the root of your project (where `app.py` is) and run:
```bash
npm create vite@latest admin-ui -- --template react
cd admin-ui
npm install
npm install @microsoft/teams-js bootstrap
```

#### Step 2: Write the React Code
In your new `admin-ui` folder, replace the contents of `src/App.jsx` with this React version of your dashboard:

```jsx
import React, { useEffect, useState } from 'react';
import * as microsoftTeams from "@microsoft/teams-js";
import 'bootstrap/dist/css/bootstrap.min.css';

const SUPER_ADMINS =["ai.vijeth@laratechconsulting.com"];

function App() {
  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState({ mcp_servers: [] });
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    // 1. Initialize MS Teams SDK
    microsoftTeams.app.initialize().then(() => {
      microsoftTeams.app.notifySuccess();
      
      microsoftTeams.app.getContext().then((context) => {
        const userEmail = context.user?.userPrincipalName;
        console.log("🔒 RBAC Check - Logged in as:", userEmail);

        if (SUPER_ADMINS.includes(userEmail)) {
          setAuthorized(true);
          fetchData();
          // Auto-refresh logs every 10 seconds
          const interval = setInterval(fetchLogs, 10000);
          return () => clearInterval(interval);
        } else {
          setAuthorized(false);
        }
        setLoading(false);
      });
    }).catch((err) => {
      console.warn("Not in Teams context.", err);
      setAuthorized(false);
      setLoading(false);
    });
  },[]);

  const fetchData = async () => {
    fetchConfig();
    fetchLogs();
  };

  const fetchConfig = async () => {
    // Because React is served by Python, we use relative URLs!
    const res = await fetch('/api/admin/config');
    const data = await res.json();
    setConfig(data);
  };

  const fetchLogs = async () => {
    const res = await fetch('/api/admin/logs');
    const data = await res.json();
    setLogs(data);
  };

  const toggleServer = async (index, isEnabled) => {
    const newConfig = { ...config };
    newConfig.mcp_servers[index].enabled = isEnabled;
    setConfig(newConfig); // Optimistic UI update

    await fetch('/api/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newConfig)
    });
  };

  if (loading) return <div className="container mt-5 text-center"><h5>Loading Security Context...</h5></div>;

  if (!authorized) {
    return (
      <div className="container text-center mt-5">
        <h1 className="text-danger">🔒 Access Denied</h1>
        <p>You do not have administrative privileges to view this dashboard inside Microsoft Teams.</p>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ backgroundColor: '#f5f5f5', minHeight: '100vh', padding: '20px' }}>
      <h2 className="mb-4">🛡️ ITSM AI Command Center</h2>
      
      <div className="row">
        {/* MCP Server Controls */}
        <div className="col-md-4">
          <div className="card mb-4 shadow-sm">
            <div className="card-header bg-dark text-white">🔌 MCP Microservices</div>
            <div className="card-body">
              {config.mcp_servers.map((server, index) => (
                <div className="form-check form-switch mb-3" key={index}>
                  <input 
                    className="form-check-input" 
                    type="checkbox" 
                    id={`mcp-${index}`}
                    checked={server.enabled}
                    onChange={(e) => toggleServer(index, e.target.checked)} 
                  />
                  <label className="form-check-label" htmlFor={`mcp-${index}`}>
                    <strong>{server.name}</strong><br/>
                    <small className="text-muted">{server.description}</small>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Live Audit Logs */}
        <div className="col-md-8">
          <div className="card shadow-sm">
            <div className="card-header bg-primary text-white d-flex justify-content-between align-items-center">
              <span>📡 Live Audit Logs</span>
              <button className="btn btn-sm btn-light" onClick={fetchLogs}>Refresh</button>
            </div>
            <div className="card-body" style={{ height: '500px', overflowY: 'auto' }}>
              <table className="table table-sm">
                <thead><tr><th>Time</th><th>User</th><th>Action</th><th>Details</th></tr></thead>
                <tbody>
                  {logs.map((log, i) => (
                    <tr key={i}>
                      <td className="text-muted" style={{ width: '100px' }}>
                        {new Date(log.timestamp).toLocaleTimeString()}
                      </td>
                      <td><small>{log.user_email}</small></td>
                      <td style={{ 
                        color: log.role === 'user' ? '#0d6efd' : log.role === 'bot' ? '#198754' : '#6c757d',
                        fontWeight: log.role !== 'tool' ? 'bold' : 'normal',
                        fontStyle: log.role === 'tool' ? 'italic' : 'normal'
                      }}>
                        {log.role === 'user' ? 'User Said' : log.role === 'bot' ? 'Bot Replied' : `⚙️ ${log.tool_name}`}
                      </td>
                      <td>
                        <div style={{ maxHeight: '60px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                          {log.message.substring(0, 150)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
```

#### Step 3: Build the React App
Now, compile your React app into static files that Python can read.
Run this inside your `admin-ui` folder:
```bash
npm run build
```
*(This creates a `dist` folder inside `admin-ui` containing your optimized HTML, JS, and CSS).*

#### Step 4: Update Python (`app.py`) to Serve the React App
Finally, we need to update `app.py`. We will remove the old `serve_admin_dashboard` function that read the single `admin.html`, and tell Python to serve the React `dist` folder instead.

Update your `app.py` routing section:

```python
# =========================================================
# 🚀 ADMIN DASHBOARD (Serving React Build)
# =========================================================

# Remove the old serve_admin_dashboard function.
# Add a function to serve the React index.html
async def serve_react_app(req: web.Request) -> web.Response:
    try:
        # Point this to your new React dist folder
        return web.FileResponse(os.path.join("admin-ui", "dist", "index.html"))
    except Exception as e:
        return web.Response(status=404, text=f"React build not found. Did you run 'npm run build'? Error: {str(e)}")

# ... keep api_get_logs, api_get_config, api_update_config as they are ...

# =========================================================
# --- APP INIT
# =========================================================

app = web.Application(middlewares=[teams_iframe_middleware])

app.router.add_post("/api/messages", messages)
app.router.add_post("/api/notify", notify)

# --- 🟢 REACT FRONTEND ROUTES 🟢 ---
# 1. Serve the index.html on the /admin route
app.router.add_get("/admin", serve_react_app)

# 2. Serve the static JS/CSS assets generated by Vite
# This assumes your React app is built into admin-ui/dist/assets
app.router.add_static("/assets", path=os.path.join("admin-ui", "dist", "assets"), name="assets")

# --- BACKEND API ROUTES ---
app.router.add_get("/api/admin/logs", api_get_logs)
app.router.add_get("/api/admin/config", api_get_config)
app.router.add_post("/api/admin/config", api_update_config)
```

### Why this is the "Production Way"
1. **No CORS Nightmares:** Because the frontend (React) and the backend (Python APIs) are both hosted on `https://interfaith-rubi-westerly.ngrok-free.dev`, your React app can just `fetch('/api/admin/logs')` securely without cross-origin blocks.
2. **High Performance:** Vite pre-compiles and minifies the React app into tiny static files. Python `aiohttp` is incredibly fast at serving static assets.
3. **Future-Proof:** If you decide to add complex charts (like "Tickets Created Today") or use the Microsoft Fluent UI React components later, you have the full power of `npm` at your disposal.