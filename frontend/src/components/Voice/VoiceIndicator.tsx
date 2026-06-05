import React from 'react';
import { useVoiceStore } from '../../stores/voiceStore';

const STATE_COLORS: Record<string, string> = {
  idle: '#6b7280',
  listening: '#22c55e',
  speaking: '#3b82f6',
  thinking: '#f59e0b',
  error: '#ef4444',
};

const STATE_LABELS: Record<string, string> = {
  idle: 'Idle',
  listening: 'Listening...',
  speaking: 'Speaking...',
  thinking: 'Thinking...',
  error: 'Error',
};

export function VoiceIndicator() {
  const state = useVoiceStore((s) => s.state);

  return (
    <div style={styles.container}>
      <div style={{ ...styles.dot, backgroundColor: STATE_COLORS[state] || '#6b7280' }} />
      <span style={styles.label}>{STATE_LABELS[state] || state}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 10px',
    borderRadius: 20,
    backgroundColor: '#1a1a2e',
    border: '1px solid #2a2a4a',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
    animation: 'pulse 1.5s infinite',
  },
  label: {
    fontSize: 11,
    color: '#9ca3af',
    fontWeight: 500,
  },
};
