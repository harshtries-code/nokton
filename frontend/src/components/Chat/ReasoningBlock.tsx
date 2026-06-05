import React, { useState } from 'react';

export function ReasoningBlock({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);

  if (!text) return null;

  return (
    <div style={styles.container}>
      <button style={styles.toggle} onClick={() => setExpanded(!expanded)}>
        {expanded ? '▼' : '▶'} Thinking {expanded ? '' : `(${text.length} chars)`}
      </button>
      {expanded && <div style={styles.content}>{text}</div>}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginBottom: 8,
    backgroundColor: '#111827',
    borderRadius: 8,
    padding: '6px 10px',
  },
  toggle: {
    backgroundColor: 'transparent',
    color: '#9ca3af',
    border: 'none',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    gap: 4,
  },
  content: {
    marginTop: 6,
    fontSize: 12,
    color: '#6b7280',
    fontStyle: 'italic',
    lineHeight: 1.4,
    maxHeight: 200,
    overflow: 'auto',
  },
};
