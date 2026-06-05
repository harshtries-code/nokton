import React from 'react';
import { useSettingsStore } from '../../stores/settingsStore';

export function VoiceSettings() {
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div>
      <label style={styles.label}>
        Wake word:
        <select
          value={settings.voice.wake_word.enabled ? 'on' : 'off'}
          onChange={(e) => useSettingsStore.getState().update('voice.wake_word.enabled', e.target.value === 'on')}
          style={styles.select}
        >
          <option value="off">Off</option>
          <option value="on">On</option>
        </select>
      </label>
      <label style={styles.label}>
        STT Engine:
        <select
          value={settings.voice.stt.engine}
          onChange={(e) => useSettingsStore.getState().update('voice.stt.engine', e.target.value)}
          style={styles.select}
        >
          <option value="faster-whisper">faster-whisper</option>
          <option value="google">Google (free)</option>
        </select>
      </label>
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
    marginBottom: 8,
  },
  select: {
    backgroundColor: '#111827',
    color: '#e0e0e0',
    border: '1px solid #2a2a4a',
    borderRadius: 6,
    padding: '4px 8px',
    fontSize: 13,
  },
};
