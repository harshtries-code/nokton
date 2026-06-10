import React from 'react';
import { useCostStore } from '../../stores/costStore';

function fmtCost(usd: number): string {
  if (usd === 0) return '$0.00';
  if (usd < 0.0001) return '<$0.0001';
  if (usd < 1) return `$${usd.toFixed(4)}`;
  return `$${usd.toFixed(2)}`;
}

export function CostBadge() {
  const session = useCostStore((s) => s.session);
  const total = useCostStore((s) => s.total);

  return (
    <div
      title={`Session: ${session.input_tokens ?? 0} in / ${session.output_tokens ?? 0} out\nTotal: ${total.input_tokens ?? 0} in / ${total.output_tokens ?? 0} out`}
      style={styles.badge}
    >
      <span style={styles.label}>COST:</span>
      <span style={styles.session}>{fmtCost(session.cost_usd)}</span>
      <span style={styles.separator}>│</span>
      <span style={styles.total}>Σ {fmtCost(total.cost_usd)}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 6,
    padding: '2px 8px',
    fontSize: 11,
    fontFamily: '"Share Tech Mono", monospace',
    letterSpacing: 1,
  },
  label: {
    color: 'rgba(0, 212, 255, 0.4)',
  },
  session: {
    color: '#00d4ff',
  },
  separator: {
    color: 'rgba(0, 212, 255, 0.25)',
  },
  total: {
    color: 'rgba(0, 212, 255, 0.5)',
  },
};
