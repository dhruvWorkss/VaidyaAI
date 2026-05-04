import React from 'react';
import { FiPlus, FiMessageSquare, FiActivity } from 'react-icons/fi';
import DnaLogo from './DnaLogo';

export default function Sidebar({ convos, activeId, onNew, onSelect }) {
  return (
    <div style={S.wrap}>
      <div style={S.top}>
        <div style={S.brand}>
          <DnaLogo size={28} />
          <span style={S.brandName}>VaidyaAI</span>
        </div>
        <button style={S.newBtn} onClick={onNew} title="New consultation">
          <FiPlus size={16} color="var(--text-sub)" />
        </button>
      </div>

      <div style={S.list}>
        {convos.length === 0 && (
          <div style={S.empty}>No consultations yet</div>
        )}
        {convos.map(c => (
          <button
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
    width: '220px', flexShrink: 0,
    background: 'var(--sidebar)',
    display: 'flex', flexDirection: 'column',
    height: '100vh', padding: '12px 8px',
    borderRight: '1px solid var(--border)',
  },
  top: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    padding: '4px 8px 16px',
  },
  brand: { display: 'flex', alignItems: 'center', gap: '8px' },
  brandName: { fontSize: '15px', fontWeight: '600', color: 'var(--text)' },
  newBtn: {
    width: '28px', height: '28px', borderRadius: '6px',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
  },
  list: { flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '2px' },
  empty: { fontSize: '12px', color: 'var(--text-muted)', padding: '8px 10px' },
  item: {
    display: 'flex', alignItems: 'center', gap: '8px',
    padding: '8px 10px', borderRadius: '8px',
    width: '100%', cursor: 'pointer',
    border: 'none', transition: 'background 0.15s',
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