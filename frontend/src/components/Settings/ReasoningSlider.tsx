import React from 'react';
import { useSettingsStore } from '../../stores/settingsStore';
import { getWebSocket } from '../../hooks/useWebSocket';

const EFFORTS = ['off', 'high', 'xhigh'];

export function ReasoningSlider() {
  const reasoningEffort = useSettingsStore((s) => s.settings.model.reasoning_effort);

  const handleChange = (value: string) => {
    useSettingsStore.getState().update('model.reasoning_effort', value);
    const settings = useSettingsStore.getState().settings;
    getWebSocket().setModel(settings.model.provider, settings.model.model, value);
  };

  return (
    <div style={styles.container}>
      <span style={styles.label}>Reasoning:</span>
      <div style={styles.buttons}>
        {EFFORTS.map((eff) => (
          <button
            key={eff}
            onClick={() => handleChange(eff)}
            style={{
              ...styles.btn,
              backgroundColor: reasoningEffort === eff ? '#7c3aed' : '#1f2937',
              color: reasoningEffort === eff ? '#fff' : '#9ca3af',
            }}
          >
            {eff === 'off' ? 'Off' : eff === 'high' ? 'High' : 'X-High'}
          </button>
        ))}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginTop: 8,
  },
  label: { fontSize: 13, color: '#d1d5db' },
  buttons: { display: 'flex', gap: 4 },
  btn: {
    border: 'none',
    padding: '4px 12px',
    borderRadius: 6,
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
  },
};
