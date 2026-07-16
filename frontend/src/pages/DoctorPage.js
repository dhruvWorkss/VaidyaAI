import React, { useState, useEffect } from 'react';
import { FiActivity, FiUser, FiMessageSquare, FiArrowLeft, FiRefreshCw } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown';
import DnaLogo from '../components/DnaLogo';

const RISK_CONFIG = {
  emergency: { color: '#ef4444', label: 'Emergency', bg: '#450a0a' },
  high: { color: '#f97316', label: 'High Risk', bg: '#431407' },
  medium: { color: '#eab308', label: 'Medium Risk', bg: '#422006' },
  low: { color: '#22c55e', label: 'Low Risk', bg: '#052e16' },
  null: { color: '#6b7280', label: 'Unassessed', bg: '#1f2937' },
};

export default function DoctorPage() {
  const [sessions, setSessions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/triage/sessions');
      const data = await res.json();
      setSessions(data);
    } catch {
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchSession = async (id) => {
    setDetailLoading(true);
    try {
      const res = await fetch(`http://localhost:8000/api/triage/sessions/${id}`);
      const data = await res.json();
      setSelected(data);
    } catch {
      setSelected(null);
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const formatTime = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString('en-IN', {
      day: '2-digit', month: 'short',
      hour: '2-digit', minute: '2-digit'
    });
  };

  return (
    <div style={S.page}>
      {/* Header */}
      <div style={S.header}>
        <div style={S.headerLeft}>
          <DnaLogo size={28} />
          <div>
            <div style={S.headerTitle}>Doctor Dashboard</div>
            <div style={S.headerSub}>VaidyaAI Patient Triage System</div>
          </div>
        </div>
        <div style={S.headerRight}>
          <a href="/" style={S.backBtn}>
            <FiArrowLeft size={14} />
            <span>Patient View</span>
          </a>
          <button style={S.refreshBtn} onClick={fetchSessions}>
            <FiRefreshCw size={14} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div style={S.body}>
        {/* Stats bar */}
        <div style={S.statsBar}>
          {[
            { label: 'Total Sessions', value: sessions.length, icon: '👥' },
            { label: 'Emergency', value: sessions.filter(s => s.risk_level === 'emergency').length, icon: '🚨' },
            { label: 'High Risk', value: sessions.filter(s => s.risk_level === 'high').length, icon: '🔴' },
            { label: 'Low Risk', value: sessions.filter(s => s.risk_level === 'low').length, icon: '🟢' },
          ].map((stat, i) => (
            <div key={i} style={S.statCard}>
              <div style={S.statIcon}>{stat.icon}</div>
              <div style={S.statValue}>{stat.value}</div>
              <div style={S.statLabel}>{stat.label}</div>
            </div>
          ))}
        </div>

        <div style={S.content}>
          {/* Sessions list */}
          <div style={S.sessionList}>
            <div style={S.listHeader}>
              <FiActivity size={14} color="var(--accent)" />
              <span>Patient Sessions</span>
            </div>

            {loading ? (
              <div style={S.emptyState}>Loading sessions...</div>
            ) : sessions.length === 0 ? (
              <div style={S.emptyState}>No sessions yet. Sessions will appear here once patients start consultations.</div>
            ) : (
              sessions.map(s => {
                const risk = RISK_CONFIG[s.risk_level] || RISK_CONFIG.null;
                return (
                  <div
                    key={s.id}
                    style={{
                      ...S.sessionCard,
                      border: selected?.id === s.id
                        ? `1px solid ${risk.color}`
                        : '1px solid var(--border)',
                    }}
                    onClick={() => fetchSession(s.id)}
                  >
                    <div style={S.sessionTop}>
                      <div style={S.sessionId}>
                        <FiUser size={12} color="var(--text-muted)" />
                        <span>Session {s.id.slice(-6)}</span>
                      </div>
                      <div style={{
                        ...S.riskBadge,
                        color: risk.color,
                        background: risk.bg,
                      }}>
                        {risk.label}
                      </div>
                    </div>
                    <div style={S.sessionPreview}>
                      {s.last_message || 'No messages yet'}
                    </div>
                    <div style={S.sessionMeta}>
                      <span>{s.message_count} messages</span>
                      <span>{formatTime(s.updated_at)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Session detail */}
          <div style={S.sessionDetail}>
            {!selected ? (
              <div style={S.emptyDetail}>
                <FiMessageSquare size={32} color="var(--text-muted)" />
                <p>Select a session to view the full conversation</p>
              </div>
            ) : detailLoading ? (
              <div style={S.emptyDetail}>Loading conversation...</div>
            ) : (
              <>
                <div style={S.detailHeader}>
                  <div>
                    <div style={S.detailTitle}>Session {selected.id.slice(-6)}</div>
                    <div style={S.detailMeta}>
                      {selected.messages.length} messages · {selected.language?.toUpperCase()} · {formatTime(selected.created_at)}
                    </div>
                  </div>
                  {selected.risk_level && (
                    <div style={{
                      ...S.riskBadge,
                      color: RISK_CONFIG[selected.risk_level]?.color,
                      background: RISK_CONFIG[selected.risk_level]?.bg,
                      fontSize: '13px',
                      padding: '6px 14px',
                    }}>
                      {RISK_CONFIG[selected.risk_level]?.label}
                    </div>
                  )}
                </div>

                <div style={S.conversation}>
                  {selected.messages.map((msg, i) => (
                    <div key={i} style={{
                      ...S.msgRow,
                      justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
                    }}>
                      {msg.role === 'assistant' && (
                        <div style={S.msgAvatar}>
                          <DnaLogo size={24} />
                        </div>
                      )}
                      <div style={{
                        ...(msg.role === 'user' ? S.userMsg : S.aiMsg),
                      }}>
                        {msg.role === 'assistant' ? (
                          <ReactMarkdown
                            components={{
                              p: ({ node, ...props }) => <p style={{ marginBottom: '8px', lineHeight: '1.6' }} {...props} />,
                              ul: ({ node, ...props }) => <ul style={{ paddingLeft: '16px', marginBottom: '8px' }} {...props} />,
                              li: ({ node, ...props }) => <li style={{ marginBottom: '4px' }} {...props} />,
                              strong: ({ node, ...props }) => <strong style={{ color: '#4ade80' }} {...props} />,
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          msg.content
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const S = {
  page: {
    flex: 1, display: 'flex', flexDirection: 'column',
    height: '100vh', overflow: 'hidden',
    background: 'var(--bg)',
  },
  header: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 24px',
    borderBottom: '1px solid var(--border)',
    background: 'var(--sidebar)',
    flexShrink: 0,
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: '12px' },
  headerTitle: { fontSize: '15px', fontWeight: '600', color: 'var(--text)' },
  headerSub: { fontSize: '12px', color: 'var(--text-muted)' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '8px' },
  backBtn: {
    display: 'flex', alignItems: 'center', gap: '6px',
    fontSize: '13px', color: 'var(--text-sub)',
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '6px 12px', borderRadius: '8px',
  },
  refreshBtn: {
    display: 'flex', alignItems: 'center', gap: '6px',
    fontSize: '13px', color: 'var(--text-sub)',
    background: 'var(--surface)', border: '1px solid var(--border)',
    padding: '6px 12px', borderRadius: '8px', cursor: 'pointer',
  },
  body: { flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' },
  statsBar: {
    display: 'flex', gap: '12px', padding: '16px 24px',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
  },
  statCard: {
    flex: 1, background: 'var(--surface)',
    border: '1px solid var(--border)',
    borderRadius: '10px', padding: '12px 16px',
    display: 'flex', flexDirection: 'column', gap: '4px',
  },
  statIcon: { fontSize: '18px' },
  statValue: { fontSize: '22px', fontWeight: '700', color: 'var(--text)' },
  statLabel: { fontSize: '11px', color: 'var(--text-muted)' },
  content: {
    flex: 1, display: 'flex', overflow: 'hidden',
  },
  sessionList: {
    width: '320px', flexShrink: 0,
    borderRight: '1px solid var(--border)',
    overflowY: 'auto', padding: '12px',
  },
  listHeader: {
    display: 'flex', alignItems: 'center', gap: '8px',
    fontSize: '12px', fontWeight: '600',
    color: 'var(--text-sub)', padding: '4px 8px 12px',
    textTransform: 'uppercase', letterSpacing: '0.06em',
  },
  emptyState: {
    fontSize: '13px', color: 'var(--text-muted)',
    padding: '24px 8px', textAlign: 'center', lineHeight: '1.6',
  },
  sessionCard: {
    borderRadius: '10px', padding: '12px',
    cursor: 'pointer', marginBottom: '8px',
    transition: 'border-color 0.15s',
    background: 'var(--surface)',
  },
  sessionTop: {
    display: 'flex', justifyContent: 'space-between',
    alignItems: 'center', marginBottom: '6px',
  },
  sessionId: {
    display: 'flex', alignItems: 'center', gap: '6px',
    fontSize: '12px', color: 'var(--text-muted)',
  },
  riskBadge: {
    fontSize: '11px', padding: '3px 10px',
    borderRadius: '20px', fontWeight: '500',
  },
  sessionPreview: {
    fontSize: '12px', color: 'var(--text-sub)',
    overflow: 'hidden', textOverflow: 'ellipsis',
    whiteSpace: 'nowrap', marginBottom: '8px',
  },
  sessionMeta: {
    display: 'flex', justifyContent: 'space-between',
    fontSize: '11px', color: 'var(--text-muted)',
  },
  sessionDetail: {
    flex: 1, display: 'flex', flexDirection: 'column',
    overflow: 'hidden',
  },
  emptyDetail: {
    flex: 1, display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    gap: '12px', color: 'var(--text-muted)', fontSize: '13px',
  },
  detailHeader: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 24px',
    borderBottom: '1px solid var(--border)',
    flexShrink: 0,
  },
  detailTitle: { fontSize: '15px', fontWeight: '600', color: 'var(--text)' },
  detailMeta: { fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' },
  conversation: {
    flex: 1, overflowY: 'auto',
    padding: '20px 24px',
    display: 'flex', flexDirection: 'column', gap: '16px',
  },
  msgRow: {
    display: 'flex', alignItems: 'flex-start', gap: '10px',
  },
  msgAvatar: { flexShrink: 0, marginTop: '2px' },
  userMsg: {
    background: 'var(--surface2)',
    padding: '8px 14px', borderRadius: '14px 14px 4px 14px',
    fontSize: '13px', lineHeight: '1.6', color: 'var(--text)',
    maxWidth: '70%', marginLeft: 'auto',
  },
  aiMsg: {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    padding: '12px 16px', borderRadius: '4px 14px 14px 14px',
    fontSize: '13px', lineHeight: '1.7', color: 'var(--text)',
    flex: 1,
  },
};