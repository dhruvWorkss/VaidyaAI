import React from 'react';
import { FiPlus, FiMessageSquare, FiActivity } from 'react-icons/fi';
import DnaLogo from './DnaLogo';

export default function Sidebar({ convos, activeId, onNew, onSelect }) {
  return (
    <div className="app-sidebar" style={S.wrap}>
      <div style={S.top}>
        <div style={S.brand}>
          <DnaLogo size={28} />
          <div>
            <span style={S.brandName}>Vaidya<span className="brand-accent">AI</span></span>
            <span className="brand-sub">CARE, REIMAGINED</span>
          </div>
        </div>
        <button className="new-chat-button" style={S.newBtn} onClick={onNew} title="New consultation">
          <FiPlus size={16} color="var(--text-sub)" />
        </button>
      </div>

      <div style={S.list}>
        <div className="sidebar-label">YOUR CONSULTATIONS</div>
        {convos.length === 0 && (
          <div style={S.empty}>No consultations yet</div>
        )}
        {convos.map(c => (
          <button
            className="conversation-item"
            key={c.id}
            style={{
              ...S.item,
              background: c.id === activeId ? 'var(--surface)' : 'transparent',
            }}
            onClick={() => onSelect(c.id)}
          >
            <FiMessageSquare size={13} color="var(--text-muted)" />
            <span style={S.itemTitle}>{c.title}</span>
          </button>
        ))}
      </div>

      <div style={S.bottom}>
        <div className="privacy-note"><span>●</span> Your conversation stays private</div>
        <a href="/doctor" style={S.bottomLink}>
          <FiActivity size={14} />
          <span>Doctor Dashboard</span>
        </a>
      </div>
    </div>
  );
}

const S = {
  wrap: {
    width: '248px', flexShrink: 0,
    background: 'rgba(5, 14, 18, 0.88)',
    display: 'flex', flexDirection: 'column',
    height: '100vh', padding: '18px 12px 14px',
    borderRight: '1px solid rgba(112, 255, 203, 0.12)',
  },
  top: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    padding: '4px 7px 26px',
  },
  brand: { display: 'flex', alignItems: 'center', gap: '8px' },
  brandName: { display: 'block', fontSize: '17px', fontWeight: '750', color: 'var(--text)', letterSpacing: '-0.03em' },
  newBtn: {
    width: '34px', height: '34px', borderRadius: '10px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  list: { flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' },
  empty: { fontSize: '12px', color: 'var(--text-muted)', padding: '8px 10px' },
  item: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 10px', borderRadius: '8px',
    width: '100%', cursor: 'pointer',
    border: '1px solid transparent', transition: 'all 0.2s ease',
  },
  itemTitle: {
    fontSize: '13px', color: 'var(--text-sub)',
    overflow: 'hidden', textOverflow: 'ellipsis',
    whiteSpace: 'nowrap', flex: 1, textAlign: 'left',
  },
  bottom: {
    borderTop: '1px solid var(--border)',
    paddingTop: '10px', marginTop: '8px',
  },
  bottomLink: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 10px', borderRadius: '8px',
    fontSize: '13px', color: 'var(--text-sub)',
  },
};
