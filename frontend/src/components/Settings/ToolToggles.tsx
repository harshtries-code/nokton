import React, { useState } from 'react';
import { getWebSocket } from '../../hooks/useWebSocket';

const TOOL_CATEGORIES = [
  { id: 'file_read', label: 'File Read', defaultSafe: true },
  { id: 'file_write', label: 'File Write', defaultSafe: false },
  { id: 'app_control', label: 'App Control', defaultSafe: false },
  { id: 'system_read', label: 'System Read', defaultSafe: true },
  { id: 'system_write', label: 'System Write', defaultSafe: false },
  { id: 'web', label: 'Web Access', defaultSafe: true },
  { id: 'clipboard', label: 'Clipboard', defaultSafe: true },
  { id: 'screenshot', label: 'Screenshot', defaultSafe: false },
  { id: 'terminal', label: 'Terminal', defaultSafe: false },
];

export function ToolToggles() {
  const [safeCategories, setSafeCategories] = useState<Record<string, boolean>>(
    Object.fromEntries(TOOL_CATEGORIES.map((c) => [c.id, c.defaultSafe]))
  );

  const handleToggle = (id: string, checked: boolean) => {
    setSafeCategories((s) => ({ ...s, [id]: checked }));
    const next = Object.entries(safeCategories).map(([k, v]) =>
      k === id ? [k, checked] : [k, v]
    );
    const safe = next.filter(([, v]) => v).map(([k]) => k);
    const ask = next.filter(([, v]) => !v).map(([k]) => k);
    getWebSocket().send({ type: 'settings_update', key: 'tools.permissions.safe_categories', value: safe });
    getWebSocket().send({ type: 'settings_update', key: 'tools.permissions.ask_categories', value: ask });
  };

  return (
    <div>
      {TOOL_CATEGORIES.map((cat) => (
        <label key={cat.id} style={styles.label}>
          <input
            type="checkbox"
            checked={!!safeCategories[cat.id]}
            onChange={(e) => handleToggle(cat.id, e.target.checked)}
          />
          {cat.label}
        </label>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  label: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#d1d5db',
    marginBottom: 6,
  },
};
