import React, { useEffect, useState, useCallback, useRef } from 'react';
import { app } from '@microsoft/teams-js';
import './App.css';

// MUI Core
import {
  ThemeProvider, createTheme, CssBaseline,
  Box, Typography, Tabs, Tab,
  Chip, Avatar, Tooltip, Badge,
  TextField, Switch, FormControlLabel,
  CircularProgress, Skeleton,
  Table, TableBody, TableCell,
  TableContainer, TableHead, TableRow,
  Divider, IconButton, Grid,
  Button, Snackbar, Alert,
} from '@mui/material';

// MUI Icons
import HubIcon from '@mui/icons-material/Hub';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import SearchIcon from '@mui/icons-material/Search';
import LockIcon from '@mui/icons-material/Lock';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import RefreshIcon from '@mui/icons-material/Refresh';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';
import VisibilityOffIcon from '@mui/icons-material/VisibilityOff';
import ForumIcon from '@mui/icons-material/Forum';
import InboxIcon from '@mui/icons-material/Inbox';
import PowerSettingsNewIcon from '@mui/icons-material/PowerSettingsNew';
import TuneIcon from '@mui/icons-material/Tune';

// ─── AUTH ─────────────────────────────────────────────────────────────────────
const SUPER_ADMINS = [
  'ai.vijeth@laratechconsulting.com',
  'ai.royson@laratechconsulting.com',
];

// ─── DARK THEME ───────────────────────────────────────────────────────────────
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: { main: '#6264A7', light: '#8B8DC7' },
    success: { main: '#22C55E' },
    warning: { main: '#F59E0B' },
    error: { main: '#EF4444' },
    info: { main: '#3B82F6' },
    background: { default: '#18181B', paper: '#27272A' },
    text: { primary: '#FFFFFF', secondary: '#A1A1AA', disabled: '#71717A' },
    divider: '#3F3F46',
  },
  typography: {
    fontFamily: "'Segoe UI', Inter, system-ui, sans-serif",
    fontSize: 14,
  },
  shape: { borderRadius: 8 },
  components: {
    MuiCssBaseline: {
      styleOverrides: { body: { backgroundColor: '#18181B' } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          color: '#52525B',
          fontSize: '0.75rem',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          borderBottom: '1px solid #3F3F46',
          backgroundColor: 'transparent',
          padding: '8px 16px',
        },
        body: {
          fontSize: '0.875rem',
          borderBottom: '1px solid #2D2D31',
          padding: '13px 16px',
          color: '#D4D4D8',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          color: '#71717A',
          fontWeight: 500,
          textTransform: 'none',
          fontSize: '0.875rem',
          minHeight: 42,
          px: 0,
          mr: 3,
          '&.Mui-selected': { color: '#FFFFFF', fontWeight: 600 },
        },
      },
    },
    MuiTabs: {
      styleOverrides: {
        indicator: { backgroundColor: '#FFFFFF', height: 2 },
        root: { minHeight: 42 },
      },
    },
    MuiSwitch: {
      styleOverrides: {
        switchBase: { '&.Mui-checked': { color: '#6264A7' } },
        track: { '$Mui-checked + &': { backgroundColor: '#6264A7' } },
      },
    },
  },
});

// ─── CONSTANTS ────────────────────────────────────────────────────────────────
const CHART_COLORS = ['#5B95CF', '#4CAF73', '#E05050', '#C87B2A', '#8B5CF6', '#EC4899'];

// Weekly ticket bar chart (mock — replace with real API data when available)
const WEEKLY_MOCK = [
  { day: 'Mon', count: 13 },
  { day: 'Tue', count: 18 },
  { day: 'Wed', count: 22 },
  { day: 'Thu', count: 18 },
  { day: 'Fri', count: 26 },
  { day: 'Sat', count: 8 },
  { day: 'Sun', count: 10 },
];

const MOCK_HEALTH = [
  { name: 'Azure AD Server', status: 'online', uptime: '99.9%', ping: '42ms', load: 28 },
  { name: 'ServiceNow Server', status: 'online', uptime: '99.7%', ping: '87ms', load: 55 },
  { name: 'AI Agent Core', status: 'online', uptime: '100%', ping: '12ms', load: 41 },
  { name: 'Teams Bot Framework', status: 'warning', uptime: '98.2%', ping: '210ms', load: 82 },
  { name: 'ngrok Tunnel', status: 'online', uptime: '97.5%', ping: '65ms', load: 19 },
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
    m.id, m.timestamp, m.user_email || email, m.role,
    m.tool_name || '', `"${(m.message || '').replace(/"/g, '""')}"`,
  ]);
  const csv = [header.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
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
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hr ago`;
    return new Date(ts).toLocaleDateString();
  } catch { return ts; }
}

function fmtRefreshed(date) {
  if (!date) return 'just now';
  const diff = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
  return `${Math.floor(diff / 3600)} hr ago`;
}

function getSessionStatus(session) {
  const msgs = session.messages || [];
  if (!msgs.length) return 'In Progress';
  const last = msgs[msgs.length - 1];
  if (last.role === 'bot') return 'Resolved';
  if (last.role === 'user' || last.role === 'tool') return 'Escalated';
  return 'In Progress';
}

// ─── DARK PANEL WRAPPER ───────────────────────────────────────────────────────
function Panel({ children, sx = {} }) {
  return (
    <Box sx={{ bgcolor: '#27272A', border: '1px solid #3F3F46', borderRadius: 1.5, overflow: 'hidden', ...sx }}>
      {children}
    </Box>
  );
}

// ─── KPI CARD ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, trend, trendPositive = null, loading }) {
  return (
    <Panel sx={{ p: 2.5, height: '100%', overflow: 'visible' }}>
      <Typography sx={{ fontSize: '0.65rem', fontWeight: 700, color: '#71717A', letterSpacing: '0.09em', textTransform: 'uppercase', mb: 1.5 }}>
        {label}
      </Typography>
      {loading ? (
        <>
          <Skeleton width="60%" height={52} sx={{ bgcolor: '#3F3F46', mb: 0.8 }} />
          <Skeleton width="40%" height={18} sx={{ bgcolor: '#3F3F46' }} />
        </>
      ) : (
        <>
          <Typography sx={{ fontSize: '2.6rem', fontWeight: 800, color: '#FFFFFF', lineHeight: 1.05, mb: 0.8 }}>
            {value}
          </Typography>
          <Typography sx={{ fontSize: '0.8rem', color: trendPositive === false ? '#EF4444' : '#22C55E' }}>
            {trend}
          </Typography>
        </>
      )}
    </Panel>
  );
}

// ─── STATUS BADGE ──────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    'Resolved': '#22C55E',
    'Escalated': '#F59E0B',
    'In Progress': '#3B82F6',
  };
  const color = map[status] || '#71717A';
  return (
    <Box component="span" sx={{
      display: 'inline-block', px: 1.4, py: 0.25,
      border: `1px solid ${color}`,
      borderRadius: 10,
      color,
      fontSize: '0.75rem', fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {status}
    </Box>
  );
}

// ─── STATUS DOT ───────────────────────────────────────────────────────────────
function StatusDot({ status }) {
  const c = { online: '#22C55E', warning: '#F59E0B', offline: '#EF4444' }[status] || '#71717A';
  const label = { online: 'Online', warning: 'Warning', offline: 'Offline' }[status] || '—';
  return (
    <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.6, px: 0.8, py: 0.25, borderRadius: 10, border: `1px solid ${c}44` }}>
      <FiberManualRecordIcon className={status === 'online' ? 'pulseDot' : ''} sx={{ fontSize: 8, color: c }} />
      <Typography sx={{ fontSize: '0.72rem', color: c, fontWeight: 600 }}>{label}</Typography>
    </Box>
  );
}

// ─── DONUT CHART (DARK) ───────────────────────────────────────────────────────
function DonutChartDark({ data, loading }) {
  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
        <Skeleton variant="circular" width={160} height={160} sx={{ bgcolor: '#3F3F46' }} />
      </Box>
    );
  }
  if (!data || data.length === 0) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 5, gap: 1 }}>
        <Typography sx={{ color: '#52525B', fontSize: '0.875rem' }}>No tool executions yet</Typography>
      </Box>
    );
  }

  const total = data.reduce((s, d) => s + d.count, 0);
  const CX = 90, CY = 90, R = 72, r = 46;
  let cur = 0;

  const slices = data.map((d, i) => {
    const deg = (d.count / total) * 359.99;
    const path = describeArc(CX, CY, R, r, cur, cur + deg);
    cur += deg;
    return { ...d, path, color: CHART_COLORS[i % CHART_COLORS.length], pct: Math.round((d.count / total) * 100) };
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'center' }}>
        <svg width={180} height={180} viewBox="0 0 180 180">
          {slices.map((s, i) => (
            <path key={i} d={s.path} fill={s.color} stroke="#27272A" strokeWidth={3}>
              <title>{s.tool}: {s.pct}%</title>
            </path>
          ))}
        </svg>
      </Box>
      {/* Legend — 2 column grid */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 16px', mt: 1.5 }}>
        {slices.map((s, i) => (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 0.8, minWidth: 0 }}>
            <Box sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: s.color, flexShrink: 0 }} />
            <Typography sx={{ fontSize: '0.75rem', color: '#A1A1AA', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {s.tool} {s.pct}%
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
}

// ─── WEEKLY BAR CHART ─────────────────────────────────────────────────────────
function WeeklyBarChart() {
  const MAX = 30;
  const CH = 120;
  const BAR_W = 28;
  const GAP = 14;
  const PAD_L = 30;
  const PAD_B = 26;
  const W = PAD_L + GAP + (BAR_W + GAP) * 7;

  return (
    <Panel sx={{ p: 2.5, height: '100%' }}>
      <Typography sx={{ fontSize: '0.875rem', color: '#A1A1AA', mb: 2 }}>
        Tickets automated — last 7 days
      </Typography>
      <svg width="100%" viewBox={`0 0 ${W} ${CH + PAD_B}`} preserveAspectRatio="xMidYMid meet">
        {/* Grid lines */}
        {[0, 10, 20, 30].map(v => {
          const y = CH - (v / MAX) * CH;
          return (
            <g key={v}>
              <line x1={PAD_L} y1={y} x2={W} y2={y} stroke="#3F3F46" strokeWidth={0.5} strokeDasharray="3 3" />
              <text x={PAD_L - 5} y={y + 4} textAnchor="end" fill="#52525B" fontSize={9}>{v}</text>
            </g>
          );
        })}
        {/* Bars */}
        {WEEKLY_MOCK.map((d, i) => {
          const x = PAD_L + GAP + i * (BAR_W + GAP);
          const h = (d.count / MAX) * CH;
          const y = CH - h;
          return (
            <g key={d.day}>
              <rect x={x} y={y} width={BAR_W} height={h} fill="#A8C4DA" rx={3} opacity={0.85} />
              <text x={x + BAR_W / 2} y={CH + 17} textAnchor="middle" fill="#71717A" fontSize={10}>{d.day}</text>
            </g>
          );
        })}
        {/* X baseline */}
        <line x1={PAD_L} y1={CH} x2={W} y2={CH} stroke="#3F3F46" strokeWidth={1} />
      </svg>
    </Panel>
  );
}

// ─── RECENT SESSIONS TABLE ────────────────────────────────────────────────────
function RecentSessionsTable({ sessions, loading }) {
  const rows = sessions.slice(0, 8).map(s => {
    const msgs = s.messages || [];
    const lastUserMsg = [...msgs].reverse().find(m => m.role === 'user');
    const toolCount = msgs.filter(m => m.role === 'tool').length;
    return {
      email: s.email,
      lastMsg: lastUserMsg?.message || '—',
      toolCount,
      status: getSessionStatus(s),
      time: fmtRelative(s.last_seen),
    };
  });

  return (
    <Panel>
      <Box sx={{ px: 2.5, py: 1.8, borderBottom: '1px solid #3F3F46' }}>
        <Typography sx={{ fontSize: '0.875rem', color: '#A1A1AA' }}>Recent sessions</Typography>
      </Box>
      <TableContainer>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>User</TableCell>
              <TableCell>Last message</TableCell>
              <TableCell align="center">Tools used</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Time</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loading ? (
              [1, 2, 3, 4, 5].map(i => (
                <TableRow key={i}>
                  {[1, 2, 3, 4, 5].map(j => (
                    <TableCell key={j}><Skeleton sx={{ bgcolor: '#3F3F46' }} /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ py: 5, color: '#52525B', borderBottom: 'none' }}>
                  No sessions yet — start chatting with the bot to see data here.
                </TableCell>
              </TableRow>
            ) : rows.map((row, i) => (
              <TableRow key={i} sx={{ '&:last-child td': { borderBottom: 'none' }, '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                <TableCell sx={{ fontWeight: 500, color: '#E4E4E7', maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {row.email}
                </TableCell>
                <TableCell sx={{ maxWidth: 240 }}>
                  <Typography noWrap sx={{ fontSize: '0.875rem', color: '#A1A1AA' }}>{row.lastMsg}</Typography>
                </TableCell>
                <TableCell align="center">
                  <Typography sx={{ fontSize: '0.875rem', fontWeight: 600, color: '#E4E4E7' }}>{row.toolCount}</Typography>
                </TableCell>
                <TableCell><StatusBadge status={row.status} /></TableCell>
                <TableCell sx={{ color: '#71717A', fontSize: '0.82rem', whiteSpace: 'nowrap' }}>{row.time}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Panel>
  );
}

// ─── OVERVIEW TAB ─────────────────────────────────────────────────────────────
function OverviewTab({ stats, statsLoading, sessions, sessionsLoading }) {
  const tickets = stats?.tickets_week ?? 0;
  const today = stats?.tickets_today ?? 0;
  const users = stats?.unique_users ?? 0;

  return (
    <Box>
      {/* KPI Row */}
      <Grid container spacing={2} sx={{ mb: 2.5 }}>
        {[
          {
            label: 'Tickets Automated',
            value: tickets,
            trend: `+${today} today`,
          },
          {
            label: 'Unique Users Assisted',
            value: users,
            trend: users > 0 ? `+${Math.max(1, Math.round(users * 0.07))} today` : '0 today',
          },
          {
            label: 'Avg Resolution Time',
            value: <>3.2<span style={{ fontSize: '1.3rem', fontWeight: 400, marginLeft: 2 }}>min</span></>,
            trend: '-1.1 min vs last week',
          },
        ].map((k, i) => (
          <Grid key={i} item xs={12} sm={6} md={4}>
            <KpiCard {...k} loading={statsLoading} />
          </Grid>
        ))}
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={2} sx={{ mb: 2.5 }}>
        <Grid item xs={12} md={5}>
          <Panel sx={{ p: 2.5, height: '100%' }}>
            <Typography sx={{ fontSize: '0.875rem', color: '#A1A1AA', mb: 2 }}>Tool usage breakdown</Typography>
            <DonutChartDark data={stats?.tool_usage} loading={statsLoading} />
          </Panel>
        </Grid>
        <Grid item xs={12} md={7}>
          <WeeklyBarChart />
        </Grid>
      </Grid>

      {/* Recent Sessions */}
      <RecentSessionsTable sessions={sessions} loading={sessionsLoading} />
    </Box>
  );
}

// ─── CHAT BUBBLE ──────────────────────────────────────────────────────────────
function ChatBubble({ msg }) {
  const isUser = msg.role === 'user';
  const isBot = msg.role === 'bot';

  if (msg.role === 'tool') {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
        <Box sx={{
          display: 'inline-flex', alignItems: 'flex-start', gap: 0.8,
          bgcolor: '#1F1F23', border: '1px solid #3F3F46',
          borderRadius: 1.5, px: 1.5, py: 0.8, maxWidth: '80%',
        }}>
          <Typography sx={{ fontSize: '0.85rem', flexShrink: 0 }}>⚙️</Typography>
          <Box>
            <Typography sx={{ fontSize: '0.77rem', color: '#71717A', fontStyle: 'italic', lineHeight: 1.5 }}>
              {msg.tool_name && <strong style={{ color: '#A1A1AA' }}>{msg.tool_name} → </strong>}
              {msg.message}
            </Typography>
            <Typography sx={{ fontSize: '0.67rem', color: '#52525B' }}>{fmtTime(msg.timestamp)}</Typography>
          </Box>
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start', mb: 1.2, px: 1 }}>
      {isBot && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: '#1A3A28', mr: 1, mt: 0.5, flexShrink: 0 }}>
          <SmartToyIcon sx={{ fontSize: 15, color: '#22C55E' }} />
        </Avatar>
      )}
      <Box sx={{ maxWidth: '70%' }}>
        <Box sx={{
          px: 1.8, py: 1.2,
          bgcolor: isUser ? '#3B4FBF' : '#1A2E1A',
          color: isUser ? '#E8EEFF' : '#86EFAC',
          borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
          boxShadow: '0 2px 8px rgba(0,0,0,0.35)',
        }}>
          <Typography sx={{ fontSize: '0.875rem', lineHeight: 1.55, wordBreak: 'break-word' }}>
            {msg.message}
          </Typography>
        </Box>
        <Typography sx={{ fontSize: '0.68rem', color: '#52525B', mt: 0.3, px: 0.5, textAlign: isUser ? 'right' : 'left' }}>
          {fmtTime(msg.timestamp)}
        </Typography>
      </Box>
      {isUser && (
        <Avatar sx={{ width: 28, height: 28, bgcolor: '#3B4FBF', ml: 1, mt: 0.5, flexShrink: 0, fontSize: '0.75rem', fontWeight: 700 }}>
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
    <Box sx={{
      width: { xs: '100%', md: 272 },
      flexShrink: 0,
      borderRight: '1px solid #3F3F46',
      display: 'flex',
      flexDirection: 'column',
      bgcolor: '#1F1F23',
      height: '100%',
      overflow: 'hidden',
    }}>
      <Box sx={{ px: 2, py: 1.4, borderBottom: '1px solid #3F3F46' }}>
        <Typography sx={{ fontSize: '0.72rem', fontWeight: 700, color: '#52525B', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Users · {filtered.length}
        </Typography>
      </Box>

      <Box sx={{ flex: 1, overflowY: 'auto' }}>
        {filtered.length === 0 ? (
          <Box sx={{ py: 8, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
            <InboxIcon sx={{ fontSize: 38, color: '#3F3F46' }} />
            <Typography sx={{ fontSize: '0.82rem', color: '#52525B', textAlign: 'center', px: 2 }}>
              {searchQuery ? 'No users match your search.' : 'No sessions yet.'}
            </Typography>
          </Box>
        ) : filtered.map(session => {
          const sel = selectedEmail === session.email;
          const lastUserMsg = [...(session.messages || [])].reverse().find(m => m.role === 'user');
          return (
            <Box
              key={session.email}
              onClick={() => onSelect(session.email)}
              sx={{
                px: 1.8, py: 1.4,
                display: 'flex', alignItems: 'center', gap: 1.5,
                cursor: 'pointer',
                borderBottom: '1px solid #2A2A2F',
                borderLeft: sel ? '2px solid #6264A7' : '2px solid transparent',
                bgcolor: sel ? 'rgba(98,100,167,0.11)' : 'transparent',
                transition: 'all 0.14s',
                '&:hover': { bgcolor: sel ? 'rgba(98,100,167,0.11)' : 'rgba(255,255,255,0.035)' },
              }}
            >
              <Avatar sx={{ width: 36, height: 36, bgcolor: sel ? '#6264A7' : '#3F3F46', fontSize: '0.85rem', fontWeight: 700, flexShrink: 0 }}>
                {session.email[0].toUpperCase()}
              </Avatar>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography sx={{ fontSize: '0.82rem', fontWeight: sel ? 700 : 500, color: sel ? '#fff' : '#D4D4D8' }} noWrap>
                  {session.email}
                </Typography>
                <Typography sx={{ fontSize: '0.73rem', color: '#71717A' }} noWrap>
                  {lastUserMsg?.message?.slice(0, 36) || '—'}
                  {(lastUserMsg?.message?.length || 0) > 36 ? '…' : ''}
                </Typography>
              </Box>
              <Typography sx={{ fontSize: '0.65rem', color: '#52525B', flexShrink: 0 }}>
                {fmtRelative(session.last_seen)}
              </Typography>
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
    if (chatEndRef.current) chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
  }, [session?.email, hideSystem]);

  if (!session) {
    return (
      <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 2, bgcolor: '#18181B' }}>
        <ForumIcon sx={{ fontSize: 54, color: '#2D2D31' }} />
        <Typography sx={{ fontSize: '0.95rem', color: '#52525B', fontWeight: 600 }}>Select a user to view their chat</Typography>
        <Typography sx={{ fontSize: '0.8rem', color: '#3F3F46', textAlign: 'center', maxWidth: 260 }}>
          Click any name from the left panel to load the full conversation history.
        </Typography>
      </Box>
    );
  }

  let messages = session.messages || [];
  if (hideSystem) messages = messages.filter(m => m.role !== 'tool');
  if (searchQuery) {
    messages = messages.filter(m =>
      m.message?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.tool_name?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0, overflow: 'hidden' }}>
      {/* Chat header */}
      <Box sx={{ px: 2.5, py: 1.5, borderBottom: '1px solid #3F3F46', bgcolor: '#1F1F23', display: 'flex', alignItems: 'center', gap: 1.5 }}>
        <Avatar sx={{ width: 32, height: 32, bgcolor: '#6264A7', fontSize: '0.85rem', fontWeight: 700 }}>
          {session.email[0].toUpperCase()}
        </Avatar>
        <Box sx={{ flex: 1 }}>
          <Typography sx={{ fontSize: '0.875rem', fontWeight: 600, color: '#fff' }}>{session.email}</Typography>
          <Typography sx={{ fontSize: '0.72rem', color: '#71717A' }}>
            {session.message_count} messages · {fmtRelative(session.last_seen)}
          </Typography>
        </Box>
        <Box sx={{ px: 1.4, py: 0.3, borderRadius: 10, border: '1px solid #3F3F46' }}>
          <Typography sx={{ fontSize: '0.7rem', color: '#71717A' }}>{messages.length} shown</Typography>
        </Box>
      </Box>

      {/* Messages */}
      <Box className="chat-scroll" sx={{ flex: 1, overflowY: 'auto', px: 1, py: 2, bgcolor: '#18181B' }}>
        {messages.length === 0 ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', pt: 6 }}>
            <Typography sx={{ fontSize: '0.82rem', color: '#52525B' }}>
              {hideSystem ? 'No user/bot messages.' : searchQuery ? 'No matches.' : 'No messages.'}
            </Typography>
          </Box>
        ) : messages.map((msg, i) => <ChatBubble key={msg.id || i} msg={msg} />)}
        <div ref={chatEndRef} />
      </Box>
    </Box>
  );
}

// ─── LIVE SESSIONS TAB ────────────────────────────────────────────────────────
function LiveSessionsTab({ sessions, sessionsLoading, onRefresh }) {
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [hideSystem, setHideSystem] = useState(false);
  const [spinning, setSpinning] = useState(false);

  const session = sessions.find(s => s.email === selectedEmail) || null;
  const handleRefresh = async () => { setSpinning(true); await onRefresh(); setTimeout(() => setSpinning(false), 700); };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 145px)', minHeight: 500 }}>
      {/* Toolbar */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', mb: 1.5, px: 2, py: 1.2, bgcolor: '#27272A', border: '1px solid #3F3F46', borderRadius: 1.5 }}>
        <TextField
          size="small" placeholder="Search by email, ticket ID, keyword…"
          value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
          sx={{
            flex: 1, minWidth: 200,
            '& .MuiOutlinedInput-root': {
              bgcolor: '#18181B', fontSize: '0.875rem',
              '& fieldset': { borderColor: '#3F3F46' },
              '&:hover fieldset': { borderColor: '#6264A7' },
              '& input': { color: '#E4E4E7' },
            },
          }}
          InputProps={{ startAdornment: <SearchIcon sx={{ mr: 0.5, fontSize: 16, color: '#71717A' }} /> }}
        />

        <FormControlLabel
          control={<Switch size="small" checked={hideSystem} onChange={e => setHideSystem(e.target.checked)} />}
          label={
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              {hideSystem ? <VisibilityOffIcon sx={{ fontSize: 14, color: '#71717A' }} /> : <VisibilityIcon sx={{ fontSize: 14, color: '#71717A' }} />}
              <Typography sx={{ fontSize: '0.8rem', color: '#A1A1AA' }}>Hide system logs</Typography>
            </Box>
          }
          sx={{ m: 0 }}
        />

        <Box
          onClick={() => session && exportSessionCsv(session.messages, session.email)}
          sx={{
            display: 'flex', alignItems: 'center', gap: 0.6,
            px: 1.4, py: 0.6, borderRadius: 1, border: '1px solid #3F3F46',
            cursor: session ? 'pointer' : 'not-allowed', opacity: session ? 1 : 0.4,
            transition: 'all 0.14s',
            '&:hover': session ? { bgcolor: 'rgba(255,255,255,0.05)', borderColor: '#6264A7' } : {},
          }}
        >
          <DownloadIcon sx={{ fontSize: 15, color: '#A1A1AA' }} />
          <Typography sx={{ fontSize: '0.8rem', color: '#A1A1AA' }}>Export CSV</Typography>
        </Box>

        <Tooltip title="Refresh sessions">
          <IconButton size="small" onClick={handleRefresh} sx={{ color: '#71717A', '&:hover': { color: '#fff' } }}>
            <RefreshIcon className={spinning ? 'spinning' : ''} sx={{ fontSize: 18 }} />
          </IconButton>
        </Tooltip>
      </Box>

      {/* Two-Pane Inbox */}
      <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden', border: '1px solid #3F3F46', borderRadius: 1.5, bgcolor: '#18181B' }}>
        {sessionsLoading ? (
          <Box sx={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
            <CircularProgress size={28} sx={{ color: '#6264A7' }} />
            <Typography sx={{ color: '#71717A' }}>Loading sessions…</Typography>
          </Box>
        ) : (
          <>
            <SessionsSidebar sessions={sessions} selectedEmail={selectedEmail} onSelect={setSelectedEmail} searchQuery={searchQuery} />
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
              <ChatView session={session} searchQuery={searchQuery} hideSystem={hideSystem} />
            </Box>
          </>
        )}
      </Box>
    </Box>
  );
}

// ─── MCP SERVER CARD ──────────────────────────────────────────────────────────
function McpServerCard({ server, idx, onToggle, toggling }) {
  const isEnabled = !!server.enabled;
  const isTogglingThis = toggling === idx;

  return (
    <Box
      className="fadeInUp"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        p: 2,
        borderRadius: 2,
        border: '1px solid',
        borderColor: isEnabled ? 'rgba(98,100,167,0.45)' : '#3F3F46',
        bgcolor: isEnabled ? 'rgba(98,100,167,0.06)' : '#1F1F23',
        transition: 'border-color 0.25s, background-color 0.25s, box-shadow 0.25s',
        boxShadow: isEnabled ? '0 0 0 1px rgba(98,100,167,0.18) inset' : 'none',
        '&:hover': {
          borderColor: isEnabled ? 'rgba(98,100,167,0.7)' : '#52525B',
          boxShadow: '0 4px 20px rgba(0,0,0,0.35)',
        },
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Subtle top accent line */}
      <Box sx={{
        position: 'absolute', top: 0, left: 0, right: 0, height: 2,
        bgcolor: isEnabled ? '#6264A7' : 'transparent',
        transition: 'background-color 0.3s',
      }} />

      {/* Header row: icon + name + category */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 1.2 }}>
        <Box sx={{
          width: 40, height: 40, borderRadius: 1.5,
          bgcolor: isEnabled ? 'rgba(98,100,167,0.18)' : '#2D2D31',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: '1.25rem', flexShrink: 0,
          border: '1px solid',
          borderColor: isEnabled ? 'rgba(98,100,167,0.35)' : '#3F3F46',
          transition: 'all 0.25s',
        }}>
          {server.icon || '⚙️'}
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography sx={{ fontSize: '0.9rem', fontWeight: 700, color: '#E4E4E7', lineHeight: 1.2 }}>
            {server.display_name || server.name}
          </Typography>
          {server.category && (
            <Box sx={{
              display: 'inline-block', mt: 0.4,
              px: 0.8, py: 0.1,
              borderRadius: 1,
              bgcolor: 'rgba(255,255,255,0.06)',
              border: '1px solid #3F3F46',
            }}>
              <Typography sx={{ fontSize: '0.65rem', color: '#71717A', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
                {server.category}
              </Typography>
            </Box>
          )}
        </Box>
      </Box>

      {/* Description */}
      <Typography sx={{ fontSize: '0.78rem', color: '#71717A', lineHeight: 1.55, mb: 1.8, flex: 1 }}>
        {server.description}
      </Typography>

      {/* Footer: status badge + button */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        {/* Status badge */}
        <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.7 }}>
          <Box sx={{
            width: 8, height: 8, borderRadius: '50%',
            bgcolor: isEnabled ? '#22C55E' : '#EF4444',
            animation: isEnabled ? 'pulse-dot 1.6s ease-in-out infinite' : 'none',
            flexShrink: 0,
          }} />
          <Typography sx={{
            fontSize: '0.75rem',
            fontWeight: 600,
            color: isEnabled ? '#22C55E' : '#EF4444',
          }}>
            {isEnabled ? 'Running' : 'Stopped'}
          </Typography>
        </Box>

        {/* Enable / Disable button */}
        <Button
          size="small"
          variant={isEnabled ? 'outlined' : 'contained'}
          disabled={isTogglingThis}
          onClick={() => onToggle(idx, !isEnabled)}
          startIcon={isTogglingThis
            ? <CircularProgress size={12} sx={{ color: 'inherit' }} />
            : <PowerSettingsNewIcon sx={{ fontSize: '13px !important' }} />
          }
          sx={{
            fontSize: '0.72rem',
            fontWeight: 700,
            textTransform: 'none',
            borderRadius: 1.2,
            px: 1.6,
            py: 0.45,
            minWidth: 82,
            ...(isEnabled ? {
              borderColor: '#EF4444',
              color: '#EF4444',
              '&:hover': { bgcolor: 'rgba(239,68,68,0.08)', borderColor: '#EF4444' },
            } : {
              bgcolor: '#22C55E',
              color: '#052e16',
              '&:hover': { bgcolor: '#16a34a' },
              boxShadow: '0 0 12px rgba(34,197,94,0.35)',
            }),
          }}
        >
          {isTogglingThis ? 'Updating…' : isEnabled ? 'Disable' : 'Enable'}
        </Button>
      </Box>
    </Box>
  );
}

// ─── MCP CONTROLS TAB ─────────────────────────────────────────────────────────
function McpControlsTab({ config, onToggle, configLoading }) {
  const [toggling, setToggling] = useState(null);   // idx of card being toggled
  const [snackbar, setSnackbar] = useState(null);   // { msg, severity }

  const servers = config.mcp_servers || [];
  const runCount = servers.filter(s => s.enabled).length;
  const stopCount = servers.length - runCount;

  const handleToggle = async (idx, nextEnabled) => {
    setToggling(idx);
    try {
      await onToggle(idx, nextEnabled);
      const srv = servers[idx];
      setSnackbar({
        msg: `${srv.display_name || srv.name} ${nextEnabled ? 'enabled' : 'disabled'} successfully`,
        severity: nextEnabled ? 'success' : 'warning',
      });
    } catch {
      setSnackbar({ msg: 'Failed to update server status.', severity: 'error' });
    } finally {
      setToggling(null);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1.5, mb: 2.5 }}>
        <Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.4 }}>
            <TuneIcon sx={{ fontSize: 18, color: '#6264A7' }} />
            <Typography sx={{ fontSize: '1.05rem', fontWeight: 700, color: '#fff' }}>MCP Server Controls</Typography>
          </Box>
          <Typography sx={{ fontSize: '0.82rem', color: '#71717A' }}>
            Toggle microservices on or off. Changes apply immediately to the bot routing layer.
          </Typography>
        </Box>

        {/* Summary pills */}
        {!configLoading && (
          <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
            <Box sx={{
              display: 'flex', alignItems: 'center', gap: 0.7,
              px: 1.4, py: 0.5, borderRadius: 1.5,
              bgcolor: 'rgba(34,197,94,0.08)', border: '1px solid rgba(34,197,94,0.25)',
            }}>
              <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: '#22C55E', animation: 'pulse-dot 1.6s ease-in-out infinite' }} />
              <Typography sx={{ fontSize: '0.78rem', fontWeight: 700, color: '#22C55E' }}>{runCount} Running</Typography>
            </Box>
            <Box sx={{
              display: 'flex', alignItems: 'center', gap: 0.7,
              px: 1.4, py: 0.5, borderRadius: 1.5,
              bgcolor: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)',
            }}>
              <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: '#EF4444' }} />
              <Typography sx={{ fontSize: '0.78rem', fontWeight: 700, color: '#EF4444' }}>{stopCount} Stopped</Typography>
            </Box>
          </Box>
        )}
      </Box>

      {/* Card grid */}
      {configLoading ? (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[1, 2, 3, 4, 5, 6].map(i => (
            <Grid key={i} item xs={12} sm={6}>
              <Skeleton variant="rectangular" height={160} sx={{ borderRadius: 2, bgcolor: '#27272A' }} />
            </Grid>
          ))}
        </Grid>
      ) : servers.length === 0 ? (
        <Box sx={{ py: 8, textAlign: 'center' }}>
          <Typography sx={{ color: '#52525B', fontSize: '0.9rem' }}>No MCP servers configured in mcp_config.json.</Typography>
        </Box>
      ) : (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {servers.map((server, idx) => (
            <Grid key={idx} item xs={12} sm={6}>
              <McpServerCard
                server={server} idx={idx}
                onToggle={handleToggle}
                toggling={toggling}
              />
            </Grid>
          ))}
        </Grid>
      )}

      {/* System Health */}
      <Panel>
        <Box sx={{ px: 2.5, py: 2, borderBottom: '1px solid #3F3F46', display: 'flex', alignItems: 'center', gap: 1.5 }}>
          <Typography sx={{ fontSize: '0.875rem', fontWeight: 600, color: '#E4E4E7' }}>System Health</Typography>
          <Box sx={{ px: 1, py: 0.2, borderRadius: 5, bgcolor: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)' }}>
            <Typography sx={{ fontSize: '0.68rem', color: '#F59E0B' }}>Simulated</Typography>
          </Box>
        </Box>
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Service</TableCell>
                <TableCell align="center">Status</TableCell>
                <TableCell align="right">Uptime</TableCell>
                <TableCell align="right">Ping</TableCell>
                <TableCell>Load</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {MOCK_HEALTH.map(row => (
                <TableRow key={row.name} sx={{ '&:last-child td': { borderBottom: 'none' }, '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' } }}>
                  <TableCell sx={{ fontWeight: 500, color: '#E4E4E7' }}>{row.name}</TableCell>
                  <TableCell align="center"><StatusDot status={row.status} /></TableCell>
                  <TableCell align="right" sx={{ color: '#22C55E', fontWeight: 600, fontSize: '0.8rem' }}>{row.uptime}</TableCell>
                  <TableCell align="right" sx={{ color: parseInt(row.ping) > 150 ? '#F59E0B' : '#A1A1AA', fontSize: '0.8rem' }}>{row.ping}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Box sx={{ flex: 1, height: 5, borderRadius: 3, bgcolor: '#3F3F46', overflow: 'hidden' }}>
                        <Box sx={{ height: '100%', borderRadius: 3, width: `${row.load}%`, bgcolor: row.load > 75 ? '#F59E0B' : row.load > 50 ? '#3B82F6' : '#22C55E', transition: 'width 0.5s' }} />
                      </Box>
                      <Typography sx={{ fontSize: '0.72rem', color: '#71717A', minWidth: 28, textAlign: 'right' }}>{row.load}%</Typography>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Panel>

      {/* Snackbar feedback */}
      <Snackbar
        open={!!snackbar}
        autoHideDuration={3500}
        onClose={() => setSnackbar(null)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar(null)}
          severity={snackbar?.severity || 'success'}
          variant="filled"
          sx={{ borderRadius: 2, fontSize: '0.82rem' }}
        >
          {snackbar?.msg}
        </Alert>
      </Snackbar>
    </Box>
  );
}

// ─── LOADING SCREEN ───────────────────────────────────────────────────────────
function LoadingScreen() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 3, bgcolor: '#18181B' }}>
      <Box sx={{ p: 3, borderRadius: 3, bgcolor: '#6264A7', display: 'inline-flex' }}>
        <HubIcon sx={{ fontSize: 44, color: '#fff' }} />
      </Box>
      <CircularProgress sx={{ color: '#6264A7' }} size={34} />
      <Typography sx={{ color: '#71717A', fontSize: '0.95rem' }}>Authenticating with Microsoft Teams…</Typography>
    </Box>
  );
}

// ─── ACCESS DENIED ────────────────────────────────────────────────────────────
function AccessDeniedScreen({ message }) {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 3, bgcolor: '#18181B', p: 4 }}>
      <LockIcon sx={{ fontSize: 60, color: '#EF4444' }} />
      <Typography sx={{ fontSize: '1.4rem', fontWeight: 800, color: '#EF4444' }}>Access Denied</Typography>
      <Box sx={{ bgcolor: '#27272A', border: '1px solid #EF444455', borderRadius: 2, p: 2.5, maxWidth: 460 }}>
        <Typography sx={{ fontWeight: 700, color: '#EF4444', mb: 0.5 }}>Unauthorized</Typography>
        <Typography sx={{ color: '#A1A1AA', fontSize: '0.875rem' }}>{message}</Typography>
      </Box>
    </Box>
  );
}

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
function App() {
  const [authorized, setAuthorized] = useState(false);
  const [loading, setLoading] = useState(true);
  const [authMessage, setAuthMessage] = useState('');
  const [config, setConfig] = useState({ mcp_servers: [] });
  const [sessions, setSessions] = useState([]);
  const [stats, setStats] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [configLoading, setConfigLoading] = useState(true);
  const [statsLoading, setStatsLoading] = useState(true);
  const [sessLoading, setSessLoading] = useState(true);
  const [lastRefreshDate, setLastRefresh] = useState(null);

  // Tick every 60s so the "refreshed X min ago" label updates
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(n => n + 1), 60000);
    return () => clearInterval(id);
  }, []);

  // ── Teams SDK Init ─────────────────────────────────────────────────────────
  useEffect(() => {
    let mounted = true;
    const init = async () => {
      try {
        await Promise.race([
          app.initialize(),
          new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 3000)),
        ]);
        app.notifySuccess();
        const ctx = await app.getContext();
        const email = ctx.user?.userPrincipalName;
        if (!mounted) return;
        if (SUPER_ADMINS.includes(email)) {
          setAuthorized(true);
          fetchConfig();
          refreshAll();
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

  // ── Auto-refresh every 30 s ────────────────────────────────────────────────
  useEffect(() => {
    if (!authorized) return;
    const id = setInterval(refreshAll, 30000);
    return () => clearInterval(id);
  }, [authorized]);

  // ── API calls ──────────────────────────────────────────────────────────────
  const fetchConfig = async () => {
    setConfigLoading(true);
    try { const d = await (await fetch('/api/admin/config')).json(); setConfig(d); }
    catch (e) { console.error(e); }
    finally { setConfigLoading(false); }
  };

  const fetchStats = useCallback(async () => {
    setStatsLoading(true);
    try { const d = await (await fetch('/api/admin/stats')).json(); setStats(d); }
    catch (e) { console.error(e); }
    finally { setStatsLoading(false); }
  }, []);

  const fetchSessions = useCallback(async () => {
    setSessLoading(true);
    try { const d = await (await fetch('/api/admin/sessions')).json(); setSessions(Array.isArray(d) ? d : []); }
    catch (e) { console.error(e); }
    finally { setSessLoading(false); }
  }, []);

  function refreshAll() {
    fetchStats();
    fetchSessions();
    setLastRefresh(new Date());
  }

  const toggleServer = async (idx, isEnabled) => {
    const newCfg = { ...config, mcp_servers: config.mcp_servers.map((s, i) => i === idx ? { ...s, enabled: isEnabled } : s) };
    setConfig(newCfg);
    await fetch('/api/admin/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(newCfg) });
  };

  if (loading) return <ThemeProvider theme={darkTheme}><CssBaseline /><LoadingScreen /></ThemeProvider>;
  if (!authorized) return <ThemeProvider theme={darkTheme}><CssBaseline /><AccessDeniedScreen message={authMessage} /></ThemeProvider>;

  const refreshLabel = lastRefreshDate ? `Live — refreshed ${fmtRefreshed(lastRefreshDate)}` : 'Live';

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <Box sx={{ minHeight: '100vh', bgcolor: '#18181B', display: 'flex', flexDirection: 'column' }}>

        {/* ── Sticky header ───────────────────────────────────────── */}
        <Box sx={{ bgcolor: '#111113', borderBottom: '1px solid #27272A', position: 'sticky', top: 0, zIndex: 100 }}>
          {/* Title row */}
          <Box sx={{ px: 3, pt: 1.6, pb: 0.5, display: 'flex', alignItems: 'center' }}>
            <Typography sx={{ fontWeight: 700, fontSize: '1rem' }}>
              <span style={{ color: '#71717A' }}>ITSM{' '}</span>
              <span style={{ color: '#6264A7' }}>Admin Center</span>
            </Typography>
            <Box sx={{ flex: 1 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.2 }}>
              <Typography sx={{ fontSize: '0.77rem', color: '#52525B' }}>{refreshLabel}</Typography>
              <Tooltip title="Refresh data">
                <IconButton size="small" onClick={refreshAll} sx={{ color: '#52525B', '&:hover': { color: '#A1A1AA' } }}>
                  <RefreshIcon sx={{ fontSize: 16 }} />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>

          {/* Tabs */}
          <Tabs
            value={activeTab}
            onChange={(_, v) => setActiveTab(v)}
            sx={{ px: 3, '& .MuiTabs-flexContainer': { gap: 3 } }}
          >
            <Tab label="Overview & Analytics" value={0} />
            <Tab label="Live Chat Sessions" value={1} />
            <Tab label="MCP Server Controls" value={2} />
          </Tabs>
        </Box>

        {/* ── Page content ────────────────────────────────────────── */}
        <Box sx={{ flex: 1, p: { xs: 2, md: 3 } }}>
          {activeTab === 0 && (
            <OverviewTab
              stats={stats} statsLoading={statsLoading}
              sessions={sessions} sessionsLoading={sessLoading}
            />
          )}
          {activeTab === 1 && (
            <LiveSessionsTab
              sessions={sessions} sessionsLoading={sessLoading}
              onRefresh={fetchSessions}
            />
          )}
          {activeTab === 2 && (
            <McpControlsTab
              config={config} onToggle={toggleServer}
              configLoading={configLoading}
            />
          )}
        </Box>
      </Box>
    </ThemeProvider>
  );
}

export default App;