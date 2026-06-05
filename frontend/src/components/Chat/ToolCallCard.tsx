import React from 'react';
import { ToolCall } from '../../types/messages';

export function ToolCallCard({ toolCall }: { toolCall: ToolCall }) {
  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <span style={styles.icon}>⚙</span>
        <span style={styles.name}>{toolCall.name}</span>
        {toolCall.duration_ms && (
          <span style={styles.duration}>{toolCall.duration_ms}ms</span>
        )}
        {toolCall.result && (
          <span style={styles.status}>✓</span>
        )}
      </div>
      {toolCall.args && Object.keys(toolCall.args).length > 0 && (
        <pre style={styles.args}>{JSON.stringify(toolCall.args, null, 1)}</pre>
      )}
      {toolCall.result && (
        <div style={styles.result}>{toolCall.result}</div>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#111827',
    borderRadius: 8,
    padding: '8px 12px',
    border: '1px solid #1f2937',
    fontSize: 12,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  icon: { fontSize: 14 },
  name: { fontWeight: 600, color: '#93c5fd' },
  duration: { color: '#6b7280', marginLeft: 'auto', fontSize: 11 },
  status: { color: '#22c55e', fontWeight: 700 },
  args: {
    backgroundColor: '#0f0f23',
    padding: '4px 8px',
    borderRadius: 4,
    fontSize: 11,
    color: '#9ca3af',
    overflow: 'auto',
    maxHeight: 100,
    margin: '4px 0',
  },
  result: {
    backgroundColor: '#064e3b',
    padding: '4px 8px',
    borderRadius: 4,
    fontSize: 11,
    color: '#6ee7b7',
    maxHeight: 80,
    overflow: 'auto',
  },
};
