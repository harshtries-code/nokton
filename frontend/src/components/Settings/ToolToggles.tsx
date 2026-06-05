import React from 'react';

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
  return (
    <div>
      {TOOL_CATEGORIES.map((cat) => (
        <label key={cat.id} style={styles.label}>
          <input type="checkbox" defaultChecked={cat.defaultSafe} />
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
