import React, { useEffect, useState } from 'react';
import { app } from "@microsoft/teams-js"; // Updated import for Teams JS v2
import 'bootstrap/dist/css/bootstrap.min.css';

const SUPER_ADMINS =["ai.vijeth@laratechconsulting.com"];

function App() {
  const[authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const[authMessage, setAuthMessage] = useState("");
  const [config, setConfig] = useState({ mcp_servers: [] });
  const [logs, setLogs] = useState([]);

  // --- 1. INITIALIZATION HOOK ---
  useEffect(() => {
    let isMounted = true;

    const initTeamsApp = async () => {
      try {
        // 🔥 FIX: Force a 3-second timeout so it NEVER hangs forever
        const initPromise = app.initialize();
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Timeout waiting for Teams SDK")), 3000)
        );

        await Promise.race([initPromise, timeoutPromise]);
        app.notifySuccess();

        const context = await app.getContext();
        const userEmail = context.user?.userPrincipalName;
        console.log("🔒 RBAC Check - Logged in as:", userEmail);

        if (!isMounted) return;

        if (SUPER_ADMINS.includes(userEmail)) {
          setAuthorized(true);
          fetchConfig();
          fetchLogs();
        } else {
          setAuthorized(false);
          setAuthMessage(`Access Denied: Your email (${userEmail}) is not authorized.`);
        }
      } catch (err) {
        console.warn("⚠️ Not in Teams context or SDK failed:", err);
        if (!isMounted) return;
        setAuthorized(false);
        setAuthMessage("Must be viewed inside Microsoft Teams.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initTeamsApp();

    return () => {
      isMounted = false; // Cleanup to prevent memory leaks in React StrictMode
    };
  },[]);

  // --- 2. AUTO-REFRESH HOOK ---
  useEffect(() => {
    let intervalId;
    if (authorized) {
      // Only start the timer if they are successfully logged in
      intervalId = setInterval(fetchLogs, 10000); 
    }
    return () => clearInterval(intervalId);
  }, [authorized]);

  // --- 3. DATA FETCHING ---
  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/admin/config');
      const data = await res.json();
      setConfig(data);
    } catch (e) { console.error("Failed to load config", e); }
  };

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/admin/logs');
      const data = await res.json();
      setLogs(data);
    } catch (e) { console.error("Failed to load logs", e); }
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

  // --- 4. RENDER UI ---
  if (loading) {
    return (
      <div className="container mt-5 text-center">
        <div className="spinner-border text-primary mb-3" role="status"></div>
        <h5>Authenticating with Microsoft Teams...</h5>
      </div>
    );
  }

  if (!authorized) {
    return (
      <div className="container text-center mt-5">
        <h1 className="text-danger">🔒 Access Denied</h1>
        <p>{authMessage}</p>
      </div>
    );
  }

  return (
    <div className="container mt-4" style={{ backgroundColor: '#f5f5f5', minHeight: '100vh', padding: '20px', borderRadius: '8px' }}>
      <h2 className="mb-4">🛡️ ITSM AI Command Center</h2>
      
      <div className="row">
        {/* MCP Server Controls */}
        <div className="col-md-4">
          <div className="card mb-4 shadow-sm">
            <div className="card-header bg-dark text-white">🔌 MCP Microservices</div>
            <div className="card-body">
              {config.mcp_servers && config.mcp_servers.map((server, index) => (
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