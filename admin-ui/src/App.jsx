import React, { useEffect, useState, useCallback, useRef } from 'react';
import { app } from '@microsoft/teams-js';
import './App.css';

// MUI Core
import {
  ThemeProvider, createTheme, CssBaseline,
  Box, Drawer, AppBar, Toolbar, Typography,
  IconButton, List, ListItem, ListItemButton,
  ListItemIcon, ListItemText, Divider,
  Card, CardContent, CardHeader,
  Grid, Chip, Avatar, Tooltip, Badge,
  TextField, Switch, FormControlLabel,
  CircularProgress, LinearProgress,
  Alert, AlertTitle, Skeleton, useMediaQuery,
  Paper, Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow,
} from '@mui/material';

// MUI Icons
import MenuIcon               from '@mui/icons-material/Menu';
import HubIcon                from '@mui/icons-material/Hub';
import WarningAmberIcon       from '@mui/icons-material/WarningAmber';
import CheckCircleIcon        from '@mui/icons-material/CheckCircle';
import ErrorIcon              from '@mui/icons-material/Error';
import SmartToyIcon           from '@mui/icons-material/SmartToy';
import PersonIcon             from '@mui/icons-material/Person';
import BuildIcon              from '@mui/icons-material/Build';
import SearchIcon             from '@mui/icons-material/Search';
import LockIcon               from '@mui/icons-material/Lock';
import AccessTimeIcon         from '@mui/icons-material/AccessTime';
import FiberManualRecordIcon  from '@mui/icons-material/FiberManualRecord';
import SpeedIcon              from '@mui/icons-material/Speed';
import PowerIcon              from '@mui/icons-material/Power';
import RefreshIcon            from '@mui/icons-material/Refresh';
import ConfirmationNumberIcon from '@mui/icons-material/ConfirmationNumber';
import DownloadIcon           from '@mui/icons-material/Download';
import VisibilityIcon         from '@mui/icons-material/Visibility';
import VisibilityOffIcon      from '@mui/icons-material/VisibilityOff';
import ForumIcon              from '@mui/icons-material/Forum';
import InsightsIcon           from '@mui/icons-material/Insights';
import DateRangeIcon          from '@mui/icons-material/DateRange';
import GroupIcon              from '@mui/icons-material/Group';
import StarIcon               from '@mui/icons-material/Star';
import PeopleIcon             from '@mui/icons-material/People';
import InboxIcon              from '@mui/icons-material/Inbox';
import BarChartIcon           from '@mui/icons-material/BarChart';

// ─── AUTH ─────────────────────────────────────────────────────────────────────
const SUPER_ADMINS = [
  'ai.vijeth@laratechconsulting.com',
  'ai.royson@laratechconsulting.com',
];

// ─── TEAMS THEME ──────────────────────────────────────────────────────────────
const teamsTheme = createTheme({
  palette: {
    mode: 'light',
    primary:    { main: '#6264A7', light: '#8B8DC7', dark: '#464775', contrastText: '#fff' },
    secondary:  { main: '#464775', contrastText: '#fff' },
    success:    { main: '#13A10E' },
    warning:    { main: '#F7630C' },
    error:      { main: '#C50F1F' },
    info:       { main: '#0078D4' },
    background: { default: '#F0EFF4', paper: '#FFFFFF' },
    text:       { primary: '#201F1E', secondary: '#605E5C' },
  },
  typography: {
    fontFamily: "'Segoe UI', Inter, system-ui, sans-serif",
    fontSize: 15,
    h5:        { fontWeight: 700, fontSize: '1.3rem' },
    h6:        { fontWeight: 700, fontSize: '1.1rem' },
    h3:        { fontWeight: 800, fontSize: '2.4rem', lineHeight: 1.1 },
    subtitle1: { fontWeight: 600, fontSize: '1rem' },
    subtitle2: { fontWeight: 600, fontSize: '0.9rem' },
    body1:     { fontSize: '0.95rem' },
    body2:     { fontSize: '0.88rem' },
    caption:   { fontSize: '0.8rem' },
  },
  shape: { borderRadius: 10 },
  components: {
    MuiCard: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: {
          border: '1px solid #E1DFDD',
          borderRadius: 12,
          transition: 'box-shadow 0.2s',
          '&:hover': { boxShadow: '0 4px 24px rgba(98,100,167,0.13)' },
        },
      },
    },
    MuiCardHeader: {
      styleOverrides: {
        title:     { fontSize: '1rem', fontWeight: 700 },
        subheader: { fontSize: '0.82rem' },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600, fontSize: '0.78rem' } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 700, background: '#F0EFF4', color: '#464775', fontSize: '0.82rem', padding: '10px 14px' },
        body: { fontSize: '0.88rem', padding: '10px 14px' },
      },
    },
    MuiSwitch: {
      styleOverrides: { root: { transform: 'scale(1.1)' } },
    },
  },
});

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const DRAWER_WIDTH = 240;
const CHART_COLORS = ['#6264A7', '#0078D4', '#13A10E', '#F7630C', '#9C5714', '#C50F1F'];

const NAV_ITEMS = [
  { key: 'overview',  label: 'Overview & Analytics', icon: <InsightsIcon /> },
  { key: 'sessions',  label: 'Live Chat Sessions',   icon: <ForumIcon /> },
  { key: 'mcp',       label: 'MCP Server Controls',  icon: <HubIcon /> },
];

// ─── MOCK HEALTH DATA (visual flair) ──────────────────────────────────────────
const MOCK_HEALTH = [
  { name: 'Azure AD Server',     status: 'online',  uptime: '99.9%', ping: '42ms',  load: 28 },
  { name: 'ServiceNow Server',   status: 'online',  uptime: '99.7%', ping: '87ms',  load: 55 },
  { name: 'AI Agent Core',       status: 'online',  uptime: '100%',  ping: '12ms',  load: 41 },
  { name: 'Teams Bot Framework', status: 'warning', uptime: '98.2%', ping: '210ms', load: 82 },
  { name: 'ngrok Tunnel',        status: 'online',  uptime: '97.5%', ping: '65ms',  load: 19 },
];

// ─── HELPERS ──────────────────────────────────────────────────────────────────
function polarToCartesian(cx, cy, r, deg) {
  const rad = (deg - 90) * Math.PI / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function describeArc(cx, cy, R, r, startDeg, endDeg) {
  const s1 = polarToCartesian(cx, cy, R, startDeg);
  const e1 = polarToCartesian(cx, cy, R, endDeg);
  const s2 = polarToCartesian(cx, cy, r, endDeg);
  const e2 = polarToCartesian(cx, cy, r, startDeg);
  const large = (endDeg - startDeg) > 180 ? 1 : 0;
  return [
    `M ${s1.x.toFixed(2)} ${s1.y.toFixed(2)}`,
    `A ${R} ${R} 0 ${large} 1 ${e1.x.toFixed(2)} ${e1.y.toFixed(2)}`,
    `L ${s2.x.toFixed(2)} ${s2.y.toFixed(2)}`,
    `A ${r} ${r} 0 ${large} 0 ${e2.x.toFixed(2)} ${e2.y.toFixed(2)}`,
    'Z',
  ].join(' ');
}

function exportSessionCsv(messages, email) {
  const header = ['ID', 'Timestamp', 'User', 'Role', 'Tool', 'Message'];
  const rows = messages.map(m => [
    m.id,
    m.timestamp,
    m.user_email || email,
    m.role,
    m.tool_name || '',
    `"${(m.message || '').replace(/"/g, '""')}"`,
  ]);
  const csv = [header.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = url;
  a.download = `session_${(email || 'unknown').replace(/[@.]/g, '_')}_${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function fmtTime(ts) {
  if (!ts) return '';
  try { return new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch { return ts; }
}

function fmtRelative(ts) {
  if (!ts) return '';
  try {
    const diff = (Date.now() - new Date(ts).getTime()) / 1000;
    if (diff < 60)   return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return new Date(ts).toLocaleDateString();
  } catch { return ts; }
}

// ─── STATUS CHIP ──────────────────────────────────────────────────────────────
function StatusChip({ status }) {
  const cfg = {
    online:  { label: 'Online',  color: 'success', icon: <CheckCircleIcon sx={{ fontSize: 13 }} /> },
    offline: { label: 'Offline', color: 'error',   icon: <ErrorIcon sx={{ fontSize: 13 }} /> },
    warning: { label: 'Warning', color: 'warning', icon: <WarningAmberIcon sx={{ fontSize: 13 }} /> },
  }[status] || { label: 'Unknown', color: 'default', icon: null };
  return <Chip size="small" color={cfg.color} icon={cfg.icon} label={cfg.label} variant="outlined" />;
}

// ─── DONUT CHART ──────────────────────────────────────────────────────────────
function DonutChart({ data }) {
  if (!data || data.length === 0) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1.5, py: 4 }}>
        <BarChartIcon sx={{ fontSize: 52, color: 'text.disabled' }} />
        <Typography variant="body2" color="text.secondary" textAlign="center">
          No tool executions recorded yet.<br />Data will appear here as the bot serves users.
        </Typography>
      </Box>
    );
  }

  const total = data.reduce((s, d) => s + d.count, 0);
  const CX = 80, CY = 80, R = 62, r = 40;
  let cur = 0;

  const slices = data.map((d, i) => {
    const deg  = (d.count / total) * 359.99; // avoid full-circle SVG bug
    const path = describeArc(CX, CY, R, r, cur, cur + deg);
    cur += deg;
    return { ...d, path, color: CHART_COLORS[i % CHART_COLORS.length], pct: Math.round((d.count / total) * 100) };
  });

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 3, flexWrap: 'wrap' }}>
      <svg width={160} height={160} viewBox="0 0 160 160" style={{ flexShrink: 0 }}>
        {slices.map((s, i) => (
          <path key={i} d={s.path} fill={s.color} stroke="#fff" strokeWidth={2.5}>
            <title>{s.tool}: {s.pct}% ({s.count})</title>
          </path>
        ))}
        <text x={CX} y={CY - 6}  textAnchor="middle" fontSize={22} fontWeight="800" fill="#201F1E">{total}</text>
        <text x={CX} y={CY + 12} textAnchor="middle" fontSize={10} fill="#605E5C">tool calls</text>
      </svg>

      <Box sx={{ flex: 1, minWidth: 160 }}>
        {slices.map((s, i) => (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: s.color, flexShrink: 0 }} />
            <Typography variant="caption" sx={{ flex: 1 }} noWrap title={s.tool}>{s.tool}</Typography>
            <Chip
              size="small"
              label={`${s.pct}%`}
              sx={{ height: 20, fontSize: '0.7rem', bgcolor: s.color + '22', color: s.color, fontWeight: 700, border: 'none' }}
            />
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 24, textAlign: 'right' }}>×{s.count}</Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

// ─── OVERVIEW KPI CARDS ───────────────────────────────────────────────────────
function OverviewKpiCards({ stats, loading }) {
  const topTool = stats?.tool_usage?.[0]?.tool || '—';
  const topCount = stats?.tool_usage?.[0]?.count ?? 0;

  const cards = [
    {
      label: 'Tickets Automated Today',
      value: stats?.tickets_today ?? 0,
      icon:  <ConfirmationNumberIcon sx={{ fontSize: 26 }} />,
      color: '#6264A7', bg: '#EBEBF5',
      sub:   'ticket/incident tool calls',
      isText: false,
    },
    {
      label: 'Tickets This Week',
      value: stats?.tickets_week ?? 0,
      icon:  <DateRangeIcon sx={{ fontSize: 26 }} />,
      color: '#0078D4', bg: '#DDEEFF',
      sub:   'last 7 days',
      isText: false,
    },
    {
      label: 'Unique Users Assisted',
      value: stats?.unique_users ?? 0,
      icon:  <GroupIcon sx={{ fontSize: 26 }} />,
      color: '#13A10E', bg: '#DFFADF',
      sub:   'distinct employees served',
      isText: false,
    },
    {
      label: 'Top Tool Executed',
      value: topTool,
      icon:  <StarIcon sx={{ fontSize: 26 }} />,
      color: '#9C5714', bg: '#FFF4CE',
      sub:   `${topCount} total executions`,
      isText: true,
    },
  ];

  return (
    <Grid container spacing={2.5} sx={{ mb: 3 }}>
      {cards.map((k) => (
        <Grid item xs={6} sm={6} md={3} key={k.label}>
          <Card className="fadeInUp" sx={{ height: '100%' }}>
            <CardContent sx={{ p: { xs: 2, sm: 2.5 } }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                <Box sx={{ p: 1.2, borderRadius: 3, bgcolor: k.bg, color: k.color, display: 'flex' }}>
                  {k.icon}
                </Box>
                {loading
                  ? <Skeleton width={46} height={22} sx={{ borderRadius: 5 }} />
                  : <Chip size="small" label="Live" color="success" variant="outlined" sx={{ height: 22, fontSize: '0.7rem' }} />
                }
              </Box>

              {loading
                ? <Skeleton width="60%" height={48} />
                : k.isText
                  ? <Typography variant="h6" sx={{ color: k.color, mb: 0.5, fontWeight: 800, wordBreak: 'break-word', lineHeight: 1.2 }}>{k.value}</Typography>
                  : <Typography variant="h3" sx={{ color: k.color, mb: 0.5 }}>{k.value}</Typography>
              }
              <Typography variant="body2" color="text.secondary" fontWeight={600}>{k.label}</Typography>
              {loading
                ? <Skeleton width="40%" height={16} />
                : <Typography variant="caption" color="text.disabled">{k.sub}</Typography>
              }
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}

// ─── TOOL USAGE CARD ──────────────────────────────────────────────────────────
function ToolUsageCard({ stats, loading }) {
  return (
    <Card className="fadeInUp" sx={{ height: '100%' }}>
      <CardHeader
        title="Tool Usage Analytics"
        subheader="MCP tools executed by the AI bot"
        avatar={<Box sx={{ p: 0.8, borderRadius: 2, bgcolor: '#EBEBF5' }}><InsightsIcon sx={{ color: 'primary.main', fontSize: 20 }} /></Box>}
      />
      <Divider />
      <CardContent sx={{ pt: 2.5 }}>
        {loading ? (
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Skeleton variant="circular" width={160} height={160} />
            <Box sx={{ flex: 1 }}>
              {[1, 2, 3].map(i => <Skeleton key={i} height={24} sx={{ mb: 1.2 }} />)}
            </Box>
          </Box>
        ) : (
          <DonutChart data={stats?.tool_usage} />
        )}
      </CardContent>
    </Card>
  );
}

// ─── MCP SERVERS PANEL ────────────────────────────────────────────────────────
function McpServersPanel({ config, onToggle, loading }) {
  return (
    <Card className="fadeInUp" sx={{ height: '100%' }}>
      <CardHeader
        title="MCP Microservices"
        subheader="Toggle server connections"
        avatar={<Box sx={{ p: 0.8, borderRadius: 2, bgcolor: '#EBEBF5' }}><HubIcon sx={{ color: 'primary.main', fontSize: 20 }} /></Box>}
      />
      <Divider />
      <CardContent sx={{ pt: 2 }}>
        {loading
          ? [1, 2, 3].map(i => <Skeleton key={i} height={68} sx={{ mb: 1.5, borderRadius: 2 }} variant="rectangular" />)
          : config.mcp_servers?.length > 0
            ? config.mcp_servers.map((server, idx) => (
                <Box
                  key={idx}
                  sx={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    p: 1.8, mb: 1.5, borderRadius: 2.5, border: '1.5px solid',
                    transition: 'all 0.25s',
                    borderColor: server.enabled ? 'primary.light' : 'divider',
                    bgcolor:     server.enabled ? 'rgba(98,100,167,0.06)' : 'transparent',
                  }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <FiberManualRecordIcon
                      className={server.enabled ? 'pulseDot' : ''}
                      sx={{ fontSize: 11, color: server.enabled ? 'success.main' : 'error.main', flexShrink: 0 }}
                    />
                    <Box>
                      <Typography variant="subtitle2">{server.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{server.description}</Typography>
                    </Box>
                  </Box>
                  <Switch
                    size="small"
                    checked={!!server.enabled}
                    onChange={e => onToggle(idx, e.target.checked)}
                    color="primary"
                  />
                </Box>
              ))
            : <Alert severity="info">No MCP servers configured.</Alert>
        }
      </CardContent>
    </Card>
  );
}

// ─── SYSTEM HEALTH PANEL ──────────────────────────────────────────────────────
function SystemHealthPanel() {
  return (
    <Card className="fadeInUp">
      <CardHeader
        title="System Health"
        subheader={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 0.3 }}>
            <Chip size="small" label="Simulated" sx={{ fontSize: '0.72rem', bgcolor: '#FFF4CE', color: '#7D5700' }} />
          </Box>
        }
        avatar={<Box sx={{ p: 0.8, borderRadius: 2, bgcolor: '#DFFADF' }}><SpeedIcon sx={{ color: 'success.main', fontSize: 20 }} /></Box>}
      />
      <Divider />
      <TableContainer>
        <Table size="medium">
          <TableHead>
            <TableRow>
              <TableCell>Service</TableCell>
              <TableCell align="center" sx={{ minWidth: 90 }}>Status</TableCell>
              <TableCell align="right"  sx={{ minWidth: 70 }}>Uptime</TableCell>
              <TableCell align="right"  sx={{ minWidth: 60 }}>Ping</TableCell>
              <TableCell sx={{ minWidth: 140 }}>Load</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {MOCK_HEALTH.map((row) => (
              <TableRow key={row.name} hover>
                <TableCell>
                  <Typography variant="body2" fontWeight={600}>{row.name}</Typography>
                </TableCell>
                <TableCell align="center"><StatusChip status={row.status} /></TableCell>
                <TableCell align="right">
                  <Typography variant="body2" color="success.main" fontWeight={600}>{row.uptime}</Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" color={parseInt(row.ping) > 150 ? 'warning.main' : 'text.primary'}>{row.ping}</Typography>
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <LinearProgress
                      variant="determinate" value={row.load} sx={{ flex: 1, height: 7, borderRadius: 4 }}
                      color={row.load > 75 ? 'warning' : row.load > 50 ? 'info' : 'success'}
                    />
                    <Typography variant="caption" sx={{ minWidth: 34, textAlign: 'right' }}>{row.load}%</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Card>
  );
}

// ─── OVERVIEW TAB ─────────────────────────────────────────────────────────────
function OverviewTab({ stats, statsLoading, config, onToggle, configLoading }) {
  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 0.5 }}>Overview & Analytics</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Real-time KPIs, tool usage analytics, and infrastructure health
      </Typography>

      {/* KPI Cards */}
      <OverviewKpiCards stats={stats} loading={statsLoading} />

      {/* Tool Usage + Health */}
      <Grid container spacing={2.5} sx={{ mb: 2.5 }}>
        <Grid item xs={12} md={5}>
          <ToolUsageCard stats={stats} loading={statsLoading} />
        </Grid>
        <Grid item xs={12} md={7}>
          <SystemHealthPanel />
        </Grid>
      </Grid>

      {/* MCP Servers */}
      <Grid container spacing={2.5}>
        <Grid item xs={12} md={6}>
          <McpServersPanel config={config} onToggle={onToggle} loading={configLoading} />
        </Grid>
        <Grid item xs={12} md={6}>
          <Card className="fadeInUp">
            <CardHeader
              title="Quick Stats"
              subheader="At a glance"
              avatar={<Box sx={{ p: 0.8, borderRadius: 2, bgcolor: '#DDEEFF' }}><BarChartIcon sx={{ color: '#0078D4', fontSize: 20 }} /></Box>}
            />
            <Divider />
            <CardContent sx={{ pt: 2 }}>
              {[
                { label: 'Total tool executions', value: stats?.tool_usage?.reduce((s, t) => s + t.count, 0) ?? 0, color: '#6264A7' },
                { label: 'Tool diversity (unique)',  value: stats?.tool_usage?.length ?? 0, color: '#0078D4' },
                { label: 'Users in DB',              value: stats?.unique_users ?? 0, color: '#13A10E' },
              ].map(row => (
                <Box key={row.label} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', py: 1.4, borderBottom: '1px solid #F0EFF4' }}>
                  <Typography variant="body2" color="text.secondary">{row.label}</Typography>
                  {statsLoading
                    ? <Skeleton width={40} height={24} />
                    : <Typography variant="subtitle2" sx={{ color: row.color, fontWeight: 800 }}>{row.value}</Typography>
                  }
                </Box>
              ))}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}

// ─── CHAT BUBBLE ──────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === 'user';
  const isBot  = msg.role === 'bot';
  const isTool = msg.role === 'tool';

  if (isTool) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 0.8 }}>
        <Box
          sx={{
            display: 'inline-flex', alignItems: 'flex-start', gap: 0.8,
            bgcolor: '#F5F5F5', border: '1px solid #E0E0E0',
            borderRadius: 2, px: 1.5, py: 0.8, maxWidth: '85%',
          }}
        >
          <Typography sx={{ fontSize: '0.9rem', flexShrink: 0, mt: '1px' }}>⚙️</Typography>
          <Box>
            <Typography variant="caption" sx={{ color: '#7A7A7A', fontStyle: 'italic', lineHeight: 1.4, display: 'block' }}>
              {msg.tool_name && <strong>{msg.tool_name} → </strong>}
              {msg.message}
            </Typography>
            <Typography variant="caption" sx={{ color: '#AAAAAA', fontSize: '0.7rem' }}>{fmtTime(msg.timestamp)}</Typography>
          </Box>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', mb: 1, px: 1 }}>
      {isBot && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: '#13A10E', mr: 1, mt: 0.5, flexShrink: 0, fontSize: '0.8rem' }}>
          <SmartToyIcon sx={{ fontSize: 16 }} />
        </Avatar>
      )}

      <Box sx={{ maxWidth: '72%' }}>
        <Box
          sx={{
            px: 1.8, py: 1.2,
            bgcolor:      isUser ? '#6264A7' : '#E8F5E9',
            color:        isUser ? '#FFFFFF'  : '#1B5E20',
            borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
            boxShadow:    isUser ? '0 2px 8px rgba(98,100,167,0.25)' : '0 2px 8px rgba(0,0,0,0.07)',
          }}
        >
          <Typography variant="body2" sx={{ lineHeight: 1.55, wordBreak: 'break-word' }}>
            {msg.message}
          </Typography>
        </Box>
        <Typography variant="caption" color="text.disabled" sx={{ mt: 0.3, display: 'block', textAlign: isUser ? 'right' : 'left', px: 0.5 }}>
          {fmtTime(msg.timestamp)}
        </Typography>
      </Box>

      {isUser && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: 'primary.main', ml: 1, mt: 0.5, flexShrink: 0, fontSize: '0.75rem', fontWeight: 700 }}>
          {(msg.user_email || 'U')[0].toUpperCase()}
        </Avatar>
      )}
    </Box>
  );
}

// ─── SESSIONS SIDEBAR ─────────────────────────────────────────────────────────
function SessionsSidebar({ sessions, selectedEmail, onSelect, searchQuery }) {
  const filtered = sessions.filter(s =>
    !searchQuery ||
    s.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    s.messages.some(m => m.message?.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <Box
      sx={{
        width: { xs: '100%', md: 290 },
        flexShrink: 0,
        borderRight: '1px solid #E1DFDD',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: '#FAFAFA',
        height: '100%',
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <Box sx={{ px: 2, py: 1.5, borderBottom: '1px solid #E1DFDD', bgcolor: '#fff' }}>
        <Typography variant="subtitle2" color="text.primary">
          Active Users
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {filtered.length} session{filtered.length !== 1 ? 's' : ''}
          {searchQuery ? ' matching' : ''}
        </Typography>
      </Box>

      {/* User list */}
      <Box sx={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 6, gap: 1.5 }}>
            <InboxIcon sx={{ fontSize: 44, color: 'text.disabled' }} />
            <Typography variant="body2" color="text.secondary" textAlign="center" px={2}>
              {searchQuery ? 'No sessions match your search.' : 'No chat sessions found.'}
            </Typography>
          </Box>
        ) : filtered.map(session => {
          const selected = selectedEmail === session.email;
          const lastMsg  = session.messages[session.messages.length - 1];
          return (
            <Box
              key={session.email}
              onClick={() => onSelect(session.email)}
              sx={{
                px: 2, py: 1.5,
                display: 'flex', alignItems: 'center', gap: 1.5,
                cursor: 'pointer',
                borderBottom: '1px solid #F0EFF4',
                transition: 'all 0.18s',
                bgcolor: selected ? 'rgba(98,100,167,0.1)' : 'transparent',
                borderLeft: selected ? '3px solid #6264A7' : '3px solid transparent',
                '&:hover': { bgcolor: selected ? 'rgba(98,100,167,0.1)' : 'rgba(0,0,0,0.04)' },
              }}
            >
              <Badge
                badgeContent={session.message_count}
                max={999}
                color="primary"
                overlap="circular"
                sx={{ '& .MuiBadge-badge': { fontSize: '0.62rem', height: 17, minWidth: 17, top: 3, right: 3 } }}
              >
                <Avatar sx={{ width: 40, height: 40, bgcolor: selected ? '#6264A7' : '#8B8DC7', fontSize: '0.95rem', fontWeight: 700 }}>
                  {session.email[0].toUpperCase()}
                </Avatar>
              </Badge>

              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="body2" fontWeight={600} noWrap title={session.email}>
                  {session.email}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {lastMsg?.message?.slice(0, 45) || '—'}
                  {(lastMsg?.message?.length || 0) > 45 ? '…' : ''}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.2 }}>
                  <AccessTimeIcon sx={{ fontSize: 10, color: 'text.disabled' }} />
                  <Typography variant="caption" color="text.disabled" sx={{ fontSize: '0.68rem' }}>
                    {fmtRelative(session.last_seen)}
                  </Typography>
                </Box>
              </Box>
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

// ─── CHAT VIEW ────────────────────────────────────────────────────────────────
function ChatView({ session, searchQuery, hideSystem }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [session?.email, hideSystem]);

  if (!session) {
    return (
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2, bgcolor: '#FAFAFA' }}>
        <ForumIcon sx={{ fontSize: 64, color: 'text.disabled' }} />
        <Typography variant="h6" color="text.secondary">Select a user to view their chat</Typography>
        <Typography variant="body2" color="text.disabled" textAlign="center" sx={{ maxWidth: 320 }}>
          Click any user from the left panel to load their full conversation history with the AI bot.
        </Typography>
      </Box>
    );
  }

  let messages = session.messages;
  if (hideSystem) {
    messages = messages.filter(m => m.role !== 'tool');
  }
  if (searchQuery) {
    messages = messages.filter(m =>
      m.message?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tool_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
      {/* Chat header */}
      <Box sx={{ px: 2.5, py: 1.5, borderBottom: '1px solid #E1DFDD', bgcolor: '#fff', display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 34, height: 34, bgcolor: '#6264A7', fontSize: '0.9rem', fontWeight: 700 }}>
          {session.email[0].toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2">{session.email}</Typography>
          <Typography variant="caption" color="text.secondary">
            {session.message_count} messages · Last active {fmtRelative(session.last_seen)}
          </Typography>
        </Box>
        <Chip
          size="small"
          label={`${messages.length} shown`}
          sx={{ bgcolor: '#EBEBF5', color: '#464775', border: 'none', fontWeight: 600 }}
        />
      </Box>

      {/* Messages */}
      <Box sx={{ flex: 1, overflowY: 'auto', px: 1, py: 2 }}>
        {messages.length === 0 ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', pt: 6, gap: 1 }}>
            <Typography variant="body2" color="text.secondary">
              {hideSystem
                ? 'No user/bot messages in this session (all messages are system logs).'
                : searchQuery
                  ? 'No messages match your search.'
                  : 'No messages yet.'}
            </Typography>
          </Box>
        ) : (
          messages.map((msg, i) => <ChatBubble key={msg.id || i} msg={msg} />)
        )}
        <div ref={chatEndRef} />
      </Box>
    </Box>
  );
}

// ─── LIVE SESSIONS TAB ────────────────────────────────────────────────────────
function LiveSessionsTab({ sessions, sessionsLoading, onRefresh }) {
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [searchQuery,   setSearchQuery]   = useState('');
  const [hideSystem,    setHideSystem]    = useState(false);
  const [spinning,      setSpinning]      = useState(false);

  const session = sessions.find(s => s.email === selectedEmail) || null;

  const handleRefresh = async () => {
    setSpinning(true);
    await onRefresh();
    setTimeout(() => setSpinning(false), 700);
  };

  const handleExport = () => {
    if (!session) return;
    exportSessionCsv(session.messages, session.email);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', minHeight: 520 }}>
      {/* Page header + toolbar */}
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 0.5 }}>Live Chat Sessions</Typography>
        <Typography variant="body1" color="text.secondary">
          Two-pane inbox — click a user to audit their full AI conversation
        </Typography>
      </Box>

      {/* Toolbar */}
      <Paper
        elevation={0}
        sx={{
          display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap',
          px: 2, py: 1.2, mb: 1.5, border: '1px solid #E1DFDD', borderRadius: 2,
          bgcolor: '#fff',
        }}
      >
        <TextField
          size="small"
          placeholder="Search by user email, keyword, ticket ID…"
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          sx={{ flex: 1, minWidth: 220 }}
          InputProps={{ startAdornment: <SearchIcon sx={{ mr: 0.5, fontSize: 18, color: 'text.secondary' }} /> }}
        />

        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={hideSystem}
              onChange={e => setHideSystem(e.target.checked)}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {hideSystem ? <VisibilityOffIcon sx={{ fontSize: 15 }} /> : <VisibilityIcon sx={{ fontSize: 15 }} />}
              <Typography variant="body2">Hide system logs</Typography>
            </Box>
          }
          sx={{ m: 0 }}
        />

        <Tooltip title={session ? `Export ${session.email}'s session to CSV` : 'Select a user first'}>
          <span>
            <Chip
              icon={<DownloadIcon sx={{ fontSize: 16 }} />}
              label="Export CSV"
              onClick={handleExport}
              disabled={!session}
              sx={{
                cursor: session ? 'pointer' : 'not-allowed',
                bgcolor: session ? '#EBEBF5' : undefined,
                color:   session ? '#464775' : undefined,
                fontWeight: 600,
                '&:hover': session ? { bgcolor: '#D8D7F0' } : {},
              }}
            />
          </span>
        </Tooltip>

        <Tooltip title="Refresh sessions">
          <IconButton size="small" onClick={handleRefresh}>
            <RefreshIcon className={spinning ? 'spinning' : ''} sx={{ fontSize: 20 }} />
          </IconButton>
        </Tooltip>
      </Paper>

      {/* Two-pane inbox */}
      <Paper
        elevation={0}
        sx={{
          flex: 1,
          display: 'flex',
          overflow: 'hidden',
          border: '1px solid #E1DFDD',
          borderRadius: 2,
          bgcolor: '#fff',
        }}
      >
        {sessionsLoading ? (
          <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
            <CircularProgress size={32} />
            <Typography variant="body1" color="text.secondary">Loading sessions…</Typography>
          </Box>
        ) : (
          <>
            {/* LEFT: User sidebar */}
            <SessionsSidebar
              sessions={sessions}
              selectedEmail={selectedEmail}
              onSelect={setSelectedEmail}
              searchQuery={searchQuery}
            />

            {/* Right: Chat view */}
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
              <ChatView session={session} searchQuery={searchQuery} hideSystem={hideSystem} />
            </Box>
          </>
        )}
      </Paper>
    </Box>
  );
}

// ─── MCP CONTROLS TAB ─────────────────────────────────────────────────────────
function McpControlsTab({ config, onToggle, configLoading }) {
  return (
    <Box>
      <Typography variant="h5" gutterBottom sx={{ mb: 0.5 }}>MCP Server Controls</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Enable or disable microservice connections used by the AI bot
      </Typography>
      <Grid container spacing={2.5}>
        <Grid item xs={12} md={6}>
          <McpServersPanel config={config} onToggle={onToggle} loading={configLoading} />
        </Grid>
        <Grid item xs={12} md={6}>
          <SystemHealthPanel />
        </Grid>
      </Grid>
    </Box>
  );
}

// ─── LOADING SCREEN ───────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 3, bgcolor: '#F0EFF4' }}>
      <Box sx={{ p: 3, borderRadius: 4, bgcolor: 'primary.main', display: 'inline-flex' }}>
        <HubIcon sx={{ fontSize: 48, color: '#fff' }} />
      </Box>
      <CircularProgress color="primary" size={40} />
      <Typography variant="h6" color="text.secondary">Authenticating with Microsoft Teams…</Typography>
    </Box>
  );
}

// ─── ACCESS DENIED ────────────────────────────────────────────────────────────
function AccessDeniedScreen({ message }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 3, bgcolor: '#F0EFF4', p: 4 }}>
      <LockIcon sx={{ fontSize: 72, color: 'error.main' }} />
      <Typography variant="h4" fontWeight={800} color="error.main">Access Denied</Typography>
      <Alert severity="error" sx={{ maxWidth: 480, width: '100%' }}>
        <AlertTitle sx={{ fontSize: '1rem', fontWeight: 700 }}>Unauthorized</AlertTitle>
        <Typography variant="body1">{message}</Typography>
      </Alert>
    </Box>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
function App() {
  const [authorized,     setAuthorized]     = useState(false);
  const [loading,        setLoading]        = useState(true);
  const [authMessage,    setAuthMessage]    = useState('');
  const [config,         setConfig]         = useState({ mcp_servers: [] });
  const [sessions,       setSessions]       = useState([]);
  const [stats,          setStats]          = useState(null);
  const [activePage,     setActivePage]     = useState('overview');
  const [drawerOpen,     setDrawerOpen]     = useState(false);
  const [configLoading,  setConfigLoading]  = useState(true);
  const [statsLoading,   setStatsLoading]   = useState(true);
  const [sessionsLoading,setSessLoading]    = useState(true);

  const isMdUp = useMediaQuery(teamsTheme.breakpoints.up('md'));

  // ── Teams SDK Init ─────────────────────────────────────────────────────────
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      try {
        await Promise.race([
          app.initialize(),
          new Promise((_, rej) => setTimeout(() => rej(new Error('SDK timeout')), 3000)),
        ]);
        app.notifySuccess();
        const ctx   = await app.getContext();
        const email = ctx.user?.userPrincipalName;
        if (!mounted) return;
        if (SUPER_ADMINS.includes(email)) {
          setAuthorized(true);
          fetchConfig();
          fetchStats();
          fetchSessions();
        } else {
          setAuthMessage(`${email} is not in the super-admin list.`);
        }
      } catch {
        if (!mounted) return;
        setAuthMessage('This dashboard must be opened inside Microsoft Teams.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    init();
    return () => { mounted = false; };
  }, []);

  // ── Auto-refresh (stats + sessions every 30s) ─────────────────────────────
  useEffect(() => {
    if (!authorized) return;
    const id = setInterval(() => {
      fetchStats();
      fetchSessions();
    }, 30000);
    return () => clearInterval(id);
  }, [authorized]);

  // ── API calls ──────────────────────────────────────────────────────────────
  const fetchConfig = async () => {
    setConfigLoading(true);
    try {
      const data = await (await fetch('/api/admin/config')).json();
      setConfig(data);
    } catch (e) { console.error('fetchConfig:', e); }
    finally { setConfigLoading(false); }
  };

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const data = await (await fetch('/api/admin/stats')).json();
      setStats(data);
    } catch (e) { console.error('fetchStats:', e); }
    finally { setStatsLoading(false); }
  }, []);

  const fetchSessions = useCallback(async () => {
    setSessLoading(true);
    try {
      const data = await (await fetch('/api/admin/sessions')).json();
      setSessions(Array.isArray(data) ? data : []);
    } catch (e) { console.error('fetchSessions:', e); }
    finally { setSessLoading(false); }
  }, []);

  const toggleServer = async (idx, isEnabled) => {
    const newCfg = {
      ...config,
      mcp_servers: config.mcp_servers.map((s, i) => i === idx ? { ...s, enabled: isEnabled } : s),
    };
    setConfig(newCfg);
    await fetch('/api/admin/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newCfg),
    });
  };

  // ── Auth guards ────────────────────────────────────────────────────────────
  if (loading)     return <ThemeProvider theme={teamsTheme}><CssBaseline /><LoadingScreen /></ThemeProvider>;
  if (!authorized) return <ThemeProvider theme={teamsTheme}><CssBaseline /><AccessDeniedScreen message={authMessage} /></ThemeProvider>;

  // ── Sidebar content ────────────────────────────────────────────────────────
  const sidebarContent = (
    <Box sx={{ width: DRAWER_WIDTH, height: '100%', display: 'flex', flexDirection: 'column', bgcolor: 'secondary.main' }}>
      {/* Brand */}
      <Box sx={{ px: 2.5, py: 2.5, display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Box sx={{ p: 1, borderRadius: 2.5, bgcolor: 'rgba(255,255,255,0.18)', display: 'flex' }}>
          <HubIcon sx={{ color: '#fff', fontSize: 22 }} />
        </Box>
        <Box>
          <Typography sx={{ color: '#fff', fontWeight: 700, fontSize: '0.95rem', lineHeight: 1.2 }}>ITSM AI</Typography>
          <Typography sx={{ color: 'rgba(255,255,255,0.58)', fontSize: '0.74rem' }}>Command Center V2</Typography>
        </Box>
      </Box>
      <Divider sx={{ borderColor: 'rgba(255,255,255,0.12)' }} />

      {/* Nav items */}
      <List sx={{ px: 1, pt: 1.5, flex: 1 }}>
        {NAV_ITEMS.map(item => (
          <ListItem key={item.key} disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton
              selected={activePage === item.key}
              id={`nav-${item.key}`}
              onClick={() => { setActivePage(item.key); if (!isMdUp) setDrawerOpen(false); }}
              sx={{
                borderRadius: 2, px: 1.5, py: 1,
                color: 'rgba(255,255,255,0.72)',
                '&.Mui-selected': { bgcolor: 'rgba(255,255,255,0.16)', color: '#fff', '& .MuiListItemIcon-root': { color: '#fff' } },
                '&:hover': { bgcolor: 'rgba(255,255,255,0.1)', color: '#fff' },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36, color: 'rgba(255,255,255,0.58)' }}>{item.icon}</ListItemIcon>
              <ListItemText
                primary={item.label}
                primaryTypographyProps={{ fontSize: '0.85rem', fontWeight: activePage === item.key ? 700 : 400, lineHeight: 1.3 }}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>

      {/* Sessions count badge on sidebar */}
      {sessions.length > 0 && (
        <Box sx={{ px: 2, pb: 1.5 }}>
          <Chip
            icon={<PeopleIcon sx={{ fontSize: 14 }} />}
            label={`${sessions.length} users in DB`}
            size="small"
            sx={{ bgcolor: 'rgba(255,255,255,0.12)', color: 'rgba(255,255,255,0.7)', border: 'none', fontSize: '0.72rem', width: '100%' }}
          />
        </Box>
      )}

      <Divider sx={{ borderColor: 'rgba(255,255,255,0.12)' }} />
      <Box sx={{ px: 2, py: 1.5, display: 'flex', alignItems: 'center', gap: 1 }}>
        <PowerIcon sx={{ fontSize: 14, color: '#13A10E' }} />
        <Typography sx={{ fontSize: '0.78rem', color: 'rgba(255,255,255,0.45)' }}>All systems operational</Typography>
      </Box>
    </Box>
  );

  // ── Page router ────────────────────────────────────────────────────────────
  const renderPage = () => {
    switch (activePage) {
      case 'sessions':
        return (
          <LiveSessionsTab
            sessions={sessions}
            sessionsLoading={sessionsLoading}
            onRefresh={fetchSessions}
          />
        );
      case 'mcp':
        return (
          <McpControlsTab
            config={config}
            onToggle={toggleServer}
            configLoading={configLoading}
          />
        );
      default:
        return (
          <OverviewTab
            stats={stats}
            statsLoading={statsLoading}
            config={config}
            onToggle={toggleServer}
            configLoading={configLoading}
          />
        );
    }
  };

  // ── Layout ─────────────────────────────────────────────────────────────────
  return (
    <ThemeProvider theme={teamsTheme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>

        {/* Sidebar */}
        {isMdUp ? (
          <Drawer variant="permanent" open sx={{ width: DRAWER_WIDTH, flexShrink: 0, '& .MuiDrawer-paper': { width: DRAWER_WIDTH, border: 'none', boxSizing: 'border-box' } }}>
            {sidebarContent}
          </Drawer>
        ) : (
          <Drawer variant="temporary" open={drawerOpen} onClose={() => setDrawerOpen(false)} ModalProps={{ keepMounted: true }}
            sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH, border: 'none' } }}>
            {sidebarContent}
          </Drawer>
        )}

        {/* Right side */}
        <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          {/* AppBar */}
          <AppBar position="sticky" elevation={0}
            sx={{ bgcolor: 'primary.main', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
            <Toolbar sx={{ minHeight: 56 }}>
              {!isMdUp && (
                <IconButton edge="start" color="inherit" onClick={() => setDrawerOpen(true)} sx={{ mr: 1.5 }} aria-label="Open menu">
                  <MenuIcon />
                </IconButton>
              )}
              <Typography variant="h6" sx={{ flex: 1, fontSize: { xs: '1rem', sm: '1.1rem' } }}>
                🛡️ ITSM AI Command Center
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                {/* Live stats pill */}
                {!statsLoading && stats && (
                  <Chip
                    size="small"
                    label={`${stats.unique_users} users · ${(stats.tickets_today ?? 0)} tickets today`}
                    sx={{ bgcolor: 'rgba(255,255,255,0.15)', color: '#fff', border: 'none', fontSize: '0.75rem', display: { xs: 'none', sm: 'flex' } }}
                  />
                )}
                <Tooltip title="Refresh data" arrow>
                  <IconButton color="inherit" id="appbar-refresh" size="small"
                    onClick={() => { fetchStats(); fetchSessions(); }}>
                    <RefreshIcon />
                  </IconButton>
                </Tooltip>
                <Avatar sx={{ width: 34, height: 34, bgcolor: 'rgba(255,255,255,0.22)', fontSize: '0.95rem', fontWeight: 700 }}>A</Avatar>
              </Box>
            </Toolbar>
          </AppBar>

          {/* Main content */}
          <Box component="main" sx={{ flex: 1, p: { xs: 2, sm: 3, md: 3.5 }, bgcolor: 'background.default' }}>
            {renderPage()}
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;