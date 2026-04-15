import React, { useEffect, useMemo, useState } from 'react';
import { app } from "@microsoft/teams-js";
import 'bootstrap/dist/css/bootstrap.min.css';
import './App.css';

const SUPER_ADMINS = ["ai.vijeth@laratechconsulting.com","ai.samuel@laratechconsulting.com"];

const TABS = [
  { key: "overview", label: "Overview & Analytics" },
  { key: "sessions", label: "Live Chat Sessions" },
  { key: "mcp", label: "MCP Server Controls" }
];

function App() {
  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [authMessage, setAuthMessage] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [config, setConfig] = useState({ mcp_servers: [] });
  const [stats, setStats] = useState(null);
  const [sessions, setSessions] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [hideSystem, setHideSystem] = useState(false);

  // --- 1. INITIALIZATION HOOK ---
  useEffect(() => {
    let isMounted = true;

    const initTeamsApp = async () => {
      try {
        const initPromise = app.initialize();
        const timeoutPromise = new Promise((_, reject) =>
          setTimeout(() => reject(new Error("Timeout waiting for Teams SDK")), 3000)
        );

        await Promise.race([initPromise, timeoutPromise]);
        app.notifySuccess();

        const context = await app.getContext();
        const userEmail = context.user?.userPrincipalName;
        console.log("RBAC Check - Logged in as:", userEmail);

        if (!isMounted) return;

        if (SUPER_ADMINS.includes(userEmail)) {
          setAuthorized(true);
          fetchConfig();
          fetchStats();
          fetchSessions();
        } else {
          setAuthorized(false);
          setAuthMessage(`Access Denied: Your email (${userEmail}) is not authorized.`);
        }
      } catch (err) {
        console.warn("Not in Teams context or SDK failed:", err);
        if (!isMounted) return;
        setAuthorized(false);
        setAuthMessage("Must be viewed inside Microsoft Teams.");
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    initTeamsApp();

    return () => { isMounted = false; };
  }, []);

  // --- 2. AUTO-REFRESH ---
  useEffect(() => {
    if (!authorized) return;
    const sessionsInterval = setInterval(fetchSessions, 10000);
    const statsInterval = setInterval(fetchStats, 30000);
    return () => {
      clearInterval(sessionsInterval);
      clearInterval(statsInterval);
    };
  }, [authorized]);

  // --- 3. DATA FETCHING ---
  const fetchConfig = async () => {
    try {
      const res = await fetch('/api/admin/config');
      const data = await res.json();
      setConfig(data);
    } catch (e) { console.error("Failed to load config", e); }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch('/api/admin/stats');
      const data = await res.json();
      setStats(data);
    } catch (e) { console.error("Failed to load stats", e); }
  };

  const fetchSessions = async () => {
    try {
      const res = await fetch('/api/admin/sessions?limit=1500');
      const data = await res.json();
      const incoming = data.sessions || [];
      setSessions(incoming);
    } catch (e) { console.error("Failed to load sessions", e); }
  };

  const toggleServer = async (index, isEnabled) => {
    const newConfig = { ...config };
    newConfig.mcp_servers[index].enabled = isEnabled;
    setConfig(newConfig);

    await fetch('/api/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newConfig)
    });
  };

  const normalizedQuery = searchQuery.trim().toLowerCase();
  const filteredSessions = useMemo(() => {
    if (!normalizedQuery) return sessions;
    return sessions.filter(session =>
      (session.logs || []).some(log => {
        const msg = (log.message || "").toLowerCase();
        const tool = (log.tool_name || "").toLowerCase();
        const email = (log.user_email || "").toLowerCase();
        return msg.includes(normalizedQuery) || tool.includes(normalizedQuery) || email.includes(normalizedQuery);
      })
    );
  }, [sessions, normalizedQuery]);

  const selectedSession = useMemo(() => {
    return filteredSessions.find(s => s.user_email === selectedEmail) || filteredSessions[0] || null;
  }, [filteredSessions, selectedEmail]);

  useEffect(() => {
    if (filteredSessions.length === 0) {
      setSelectedEmail(null);
      return;
    }
    if (!filteredSessions.find(s => s.user_email === selectedEmail)) {
      setSelectedEmail(filteredSessions[0].user_email);
    }
  }, [filteredSessions, selectedEmail]);

  const formatTimestamp = (ts) => {
    if (!ts) return "";
    try { return new Date(ts).toLocaleString(); } catch { return ts; }
  };

  const getSessionPreview = (session) => {
    if (!session.logs || session.logs.length === 0) {
      return "No messages yet.";
    }
    const last = session.logs[session.logs.length - 1];
    const content = (last?.message || "").replace(/\s+/g, " ").trim();
    return content.slice(0, 70) + (content.length > 70 ? "..." : "");
  };

  const exportSessionCsv = () => {
    if (!selectedSession) return;
    const rows = [
      ["timestamp", "user_email", "role", "tool_name", "message"],
      ...selectedSession.logs.map(l => [
        l.timestamp || "",
        l.user_email || "",
        l.role || "",
        l.tool_name || "",
        (l.message || "").replace(/\r?\n/g, " ")
      ])
    ];

    const escapeCell = (value) => `"${String(value).replace(/"/g, '""')}"`;
    const csv = rows.map(r => r.map(escapeCell).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `session_${selectedSession.user_email.replace(/[^a-z0-9_-]/gi, "_")}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const visibleLogs = selectedSession
    ? selectedSession.logs.filter(l => !hideSystem || l.role !== "tool")
    : [];

  // --- 4. RENDER UI ---
  if (loading) {
    return (
      <div className="page-center">
        <div className="spinner-border text-primary mb-3" role="status"></div>
        <h5>Authenticating with Microsoft Teams...</h5>
      </div>
    );
  }

  if (!authorized) {
    return (
      <div className="page-center">
        <div className="auth-card">
          <h1>Access Denied</h1>
          <p>{authMessage}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="top-header">
        <div className="brand">
          <div className="brand-mark">ITSM</div>
          <div>
            <h1>Command Center V2</h1>
            <p>AI Service Desk Operations Console</p>
          </div>
        </div>
        <div className="header-meta">
          <div className="meta-label">Last sync</div>
          <div className="meta-value">{stats?.generated_at ? formatTimestamp(stats.generated_at) : "Loading..."}</div>
        </div>
      </header>

      <nav className="tab-nav">
        {TABS.map(tab => (
          <button
            key={tab.key}
            className={`tab-btn ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "overview" && (
        <section className="tab-panel">
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-title">Total Tickets Automated</div>
              <div className="kpi-value">{stats?.tickets?.today ?? 0}</div>
              <div className="kpi-sub">Today</div>
              <div className="kpi-foot">{stats?.tickets?.last_7_days ?? 0} in the last 7 days</div>
            </div>
            <div className="kpi-card accent">
              <div className="kpi-title">Unique Users Assisted</div>
              <div className="kpi-value">{stats?.users?.today ?? 0}</div>
              <div className="kpi-sub">Today</div>
              <div className="kpi-foot">{stats?.users?.last_7_days ?? 0} in the last 7 days</div>
            </div>
            <div className="kpi-card alt">
              <div className="kpi-title">Tool Executions</div>
              <div className="kpi-value">{stats?.tool_calls_last_7_days ?? 0}</div>
              <div className="kpi-sub">Last 7 days</div>
              <div className="kpi-foot">Operational activity across all tools</div>
            </div>
          </div>

          <div className="overview-grid">
            <div className="panel">
              <div className="panel-title">Top Tools Executed</div>
              <div className="panel-subtitle">Share of MCP tool usage (last 7 days)</div>
              <div className="tool-list">
                {(stats?.top_tools || []).map(tool => (
                  <div className="tool-row" key={tool.tool_name}>
                    <div className="tool-name">{tool.tool_name}</div>
                    <div className="tool-bar">
                      <div className="tool-bar-fill" style={{ width: `${tool.pct}%` }}></div>
                    </div>
                    <div className="tool-meta">{tool.pct}%</div>
                  </div>
                ))}
                {(!stats || (stats.top_tools || []).length === 0) && (
                  <div className="empty-state">No tool activity recorded yet.</div>
                )}
              </div>
            </div>
            <div className="panel">
              <div className="panel-title">Operational Snapshot</div>
              <div className="panel-subtitle">Service posture at a glance</div>
              <div className="snapshot-grid">
                <div>
                  <div className="snapshot-label">Enabled MCP Servers</div>
                  <div className="snapshot-value">
                    {config.mcp_servers?.filter(s => s.enabled).length || 0}
                  </div>
                </div>
                <div>
                  <div className="snapshot-label">Active Sessions Loaded</div>
                  <div className="snapshot-value">{sessions.length}</div>
                </div>
                <div>
                  <div className="snapshot-label">Search Filter</div>
                  <div className="snapshot-value">{normalizedQuery ? "Applied" : "None"}</div>
                </div>
                <div>
                  <div className="snapshot-label">System Logs Hidden</div>
                  <div className="snapshot-value">{hideSystem ? "Yes" : "No"}</div>
                </div>
              </div>
            </div>
          </div>
        </section>
      )}

      {activeTab === "sessions" && (
        <section className="tab-panel">
          <div className="sessions-toolbar">
            <div className="search-box">
              <input
                type="text"
                className="form-control"
                placeholder="Search ticket IDs, keywords, or names..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <span className="search-count">{filteredSessions.length} sessions</span>
            </div>
            <div className="toolbar-actions">
              <div className="form-check form-switch">
                <input
                  className="form-check-input"
                  type="checkbox"
                  id="hide-system"
                  checked={hideSystem}
                  onChange={(e) => setHideSystem(e.target.checked)}
                />
                <label className="form-check-label" htmlFor="hide-system">Hide System Logs</label>
              </div>
              <button className="btn btn-outline-dark" onClick={exportSessionCsv} disabled={!selectedSession}>
                Export Session CSV
              </button>
            </div>
          </div>

          <div className="sessions-layout">
            <aside className="sessions-sidebar">
              <div className="sidebar-title">Active Users</div>
              <div className="session-list">
                {filteredSessions.map(session => (
                  <button
                    key={session.user_email}
                    className={`session-item ${session.user_email === selectedSession?.user_email ? "active" : ""}`}
                    onClick={() => setSelectedEmail(session.user_email)}
                  >
                    <div className="session-email">{session.user_email}</div>
                    <div className="session-meta">
                      <span>{formatTimestamp(session.last_activity)}</span>
                      <span className="session-preview">{getSessionPreview(session)}</span>
                    </div>
                  </button>
                ))}
                {filteredSessions.length === 0 && (
                  <div className="empty-state">No sessions match the current search.</div>
                )}
              </div>
            </aside>

            <div className="chat-panel">
              {!selectedSession && (
                <div className="empty-state">Select a user to view the conversation.</div>
              )}
              {selectedSession && (
                <>
                  <div className="chat-header">
                    <div>
                      <div className="chat-title">{selectedSession.user_email}</div>
                      <div className="chat-subtitle">Last active {formatTimestamp(selectedSession.last_activity)}</div>
                    </div>
                    <div className="chat-meta">{visibleLogs.length} messages</div>
                  </div>
                  <div className="chat-thread">
                    {visibleLogs.map((log, idx) => (
                      <div key={`${log.timestamp}-${idx}`} className={`chat-row ${log.role}`}>
                        <div className={`bubble ${log.role}`}>
                          <div className="bubble-meta">
                            <span className="bubble-role">
                              {log.role === "user" ? "User" : log.role === "bot" ? "Bot" : `Tool: ${log.tool_name || "system"}`}
                            </span>
                            <span className="bubble-time">{formatTimestamp(log.timestamp)}</span>
                          </div>
                          <div className="bubble-text">{log.message}</div>
                        </div>
                      </div>
                    ))}
                    {visibleLogs.length === 0 && (
                      <div className="empty-state">No messages to display.</div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      )}

      {activeTab === "mcp" && (
        <section className="tab-panel">
          <div className="panel">
            <div className="panel-title">MCP Microservices</div>
            <div className="panel-subtitle">Toggle availability for the AI routing layer</div>
            <div className="mcp-grid">
              {config.mcp_servers && config.mcp_servers.map((server, index) => (
                <div className="mcp-card" key={index}>
                  <div className="mcp-header">
                    <div>
                      <div className="mcp-name">{server.name}</div>
                      <div className="mcp-desc">{server.description}</div>
                    </div>
                    <div className="form-check form-switch">
                      <input
                        className="form-check-input"
                        type="checkbox"
                        id={`mcp-${index}`}
                        checked={server.enabled}
                        onChange={(e) => toggleServer(index, e.target.checked)}
                      />
                    </div>
                  </div>
                  <div className={`mcp-status ${server.enabled ? "online" : "offline"}`}>
                    {server.enabled ? "Online" : "Offline"}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

export default App;
