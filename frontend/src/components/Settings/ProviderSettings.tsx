import React, { useState } from 'react';
import { getWebSocket } from '../../hooks/useWebSocket';

export function ProviderSettings() {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const providers = [
    { id: 'openrouter', name: 'OpenRouter', placeholder: 'sk-or-...' },
    { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
    { id: 'anthropic', name: 'Anthropic', placeholder: 'sk-ant-...' },
    { id: 'deepseek', name: 'DeepSeek', placeholder: 'sk-...' },
    { id: 'groq', name: 'Groq', placeholder: 'gsk_...' },
  ];

  const handleSave = (id: string) => {
    const value = keys[id] || '';
    getWebSocket().setApiKey(id, value);
    setSaved((s) => ({ ...s, [id]: true }));
    setTimeout(() => setSaved((s) => ({ ...s, [id]: false })), 1500);
  };

  return (
    <div>
      {providers.map((p) => (
        <div key={p.id} style={styles.row}>
          <span style={styles.name}>{p.name}</span>
          <input
            type="password"
            placeholder={p.placeholder}
            value={keys[p.id] || ''}
            onChange={(e) => setKeys((k) => ({ ...k, [p.id]: e.target.value }))}
            style={styles.input}
          />
          <button style={styles.btn} onClick={() => handleSave(p.id)}>
            {saved[p.id] ? '✓' : 'Save'}
          </button>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  row: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 },
  name: { width: 100, fontSize: 13, color: '#d1d5db' },
  input: {
    flex: 1,
    backgroundColor: '#111827',
    color: '#e0e0e0',
    border: '1px solid #2a2a4a',
    borderRadius: 6,
    padding: '6px 8px',
    fontSize: 13,
  },
  btn: {
    backgroundColor: '#7c3aed',
    color: '#fff',
    border: 'none',
    padding: '6px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
    minWidth: 50,
  },
};
