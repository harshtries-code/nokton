import React from 'react';

export function ErrorBanner({ message, onDismiss }: { message: string; onDismiss?: () => void }) {
  return (
    <div style={styles.banner}>
      <span style={styles.icon}>⚠</span>
      <span style={styles.message}>{message}</span>
      {onDismiss && (
        <button style={styles.dismiss} onClick={onDismiss}>✕</button>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  banner: {
    backgroundColor: '#7f1d1d',
    color: '#fca5a5',
    padding: '8px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
  },
  icon: { fontSize: 16 },
  message: { flex: 1 },
  dismiss: {
    backgroundColor: 'transparent',
    color: '#fca5a5',
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
  },
};
