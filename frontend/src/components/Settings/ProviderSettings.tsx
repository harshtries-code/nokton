import React, { useState } from 'react';
import { getWebSocket } from '../../hooks/useWebSocket';

export function ProviderSettings() {
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});

  const providers = [
    { id: 'openrouter', name: 'OpenRouter', placeholder: 'sk-or-...', hint: 'Free models available' },
    { id: 'openai', name: 'OpenAI', placeholder: 'sk-...', hint: 'GPT-4o, o1, o3' },
    { id: 'anthropic', name: 'Anthropic', placeholder: 'sk-ant-...', hint: 'Claude 4, Sonnet' },
    { id: 'google', name: 'Google AI', placeholder: 'AIza...', hint: 'Gemini 2.5 Pro/Flash' },
    { id: 'deepseek', name: 'DeepSeek', placeholder: 'sk-...', hint: 'DeepSeek V3/R1' },
    { id: 'groq', name: 'Groq', placeholder: 'gsk_...', hint: 'Fast inference' },
    { id: 'opencode', name: 'OpenCode', placeholder: 'sk-...', hint: 'OpenCode.ai models' },
    { id: 'ollama', name: 'Ollama (Local)', placeholder: 'not required', hint: 'localhost:11434' },
    { id: 'custom', name: 'Custom API', placeholder: 'your-key', hint: 'Any OpenAI-compatible' },
  ];

  const handleSave = (id: string) => {
    const value = keys[id] || '';
    getWebSocket().setApiKey(id, value);
    setSaved((s) => ({ ...s, [id]: true }));
    setTimeout(() => setSaved((s) => ({ ...s, [id]: false })), 2000);
  };

  return (
    <div style={styles.container}>
      {providers.map((p) => (
        <div key={p.id} style={styles.row}>
          <div style={styles.info}>
            <span style={styles.name}>{p.name}</span>
            <span style={styles.hint}>{p.hint}</span>
          </div>
          <input
            type="password"
            placeholder={p.placeholder}
            value={keys[p.id] || ''}
            onChange={(e) => setKeys((k) => ({ ...k, [p.id]: e.target.value }))}
            style={styles.input}
            disabled={p.id === 'ollama'}
          />
          <button
            style={saved[p.id] ? styles.btnSaved : styles.btn}
            onClick={() => handleSave(p.id)}
            disabled={p.id === 'ollama'}
          >
            {saved[p.id] ? '✓' : 'Save'}
          </button>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: { display: 'flex', flexDirection: 'column', gap: 6 },
  row: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '6px 0',
    borderBottom: '1px solid rgba(0, 212, 255, 0.06)',
  },
  info: {
    width: 120,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    flexShrink: 0,
  },
  name: { fontSize: 13, color: '#e2e8f0', fontWeight: 500 },
  hint: { fontSize: 10, color: 'rgba(0, 212, 255, 0.4)' },
  input: {
    flex: 1,
    backgroundColor: 'rgba(10, 10, 15, 0.8)',
    color: '#e2e8f0',
    border: '1px solid rgba(0, 212, 255, 0.15)',
    borderRadius: 6,
    padding: '6px 8px',
    fontSize: 12,
    fontFamily: 'inherit',
  },
  btn: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    color: '#00d4ff',
    border: '1px solid rgba(0, 212, 255, 0.25)',
    padding: '6px 14px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
    minWidth: 52,
    fontFamily: 'inherit',
    transition: 'all 0.2s ease',
  },
  btnSaved: {
    backgroundColor: 'rgba(34, 197, 94, 0.15)',
    color: '#22c55e',
    border: '1px solid rgba(34, 197, 94, 0.3)',
    padding: '6px 14px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
    minWidth: 52,
    fontFamily: 'inherit',
  },
};
