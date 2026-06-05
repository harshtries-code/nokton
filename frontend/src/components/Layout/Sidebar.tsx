import React from 'react';
import { useConversationStore } from '../../stores/conversationStore';

export function Sidebar({ onNewChat, onSettings }: { onNewChat: () => void; onSettings: () => void }) {
  const agentState = useConversationStore((s) => s.agentState);

  return (
    <div style={styles.sidebar}>
      <div style={styles.logo}>
        <h2 style={styles.logoText}>Nokton</h2>
      </div>

      <button style={styles.newChatBtn} onClick={onNewChat}>
        + New Chat
      </button>

      <div style={styles.status}>
        <div style={styles.statusDot(agentState)} />
        <span style={styles.statusText}>{agentState}</span>
      </div>

      <div style={styles.spacer} />

      <button style={styles.settingsBtn} onClick={onSettings}>
        Settings
      </button>
    </div>
  );
}

const styles: Record<string, React.CSSProperties | ((s: string) => React.CSSProperties)> = {
  sidebar: {
    width: 220,
    backgroundColor: '#1a1a2e',
    color: '#e0e0e0',
    display: 'flex',
    flexDirection: 'column',
    padding: '16px 12px',
    borderRight: '1px solid #2a2a4a',
  },
  logo: { marginBottom: 20, textAlign: 'center' },
  logoText: { margin: 0, fontSize: 20, fontWeight: 700, color: '#7c3aed' },
  newChatBtn: {
    backgroundColor: '#7c3aed',
    color: '#fff',
    border: 'none',
    padding: '10px 16px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 600,
    marginBottom: 16,
  },
  status: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 0' },
  statusDot: (state: string) => ({
    width: 8,
    height: 8,
    borderRadius: '50%',
    backgroundColor: state === 'idle' ? '#22c55e' : state === 'thinking' ? '#f59e0b' : state === 'error' ? '#ef4444' : '#6b7280',
  }),
  statusText: { fontSize: 12, textTransform: 'capitalize' },
  spacer: { flex: 1 },
  settingsBtn: {
    backgroundColor: 'transparent',
    color: '#9ca3af',
    border: '1px solid #2a2a4a',
    padding: '8px 16px',
    borderRadius: 8,
    cursor: 'pointer',
    fontSize: 13,
  },
};
