import React, { useState } from 'react';
import { ModelSelector } from './ModelSelector';
import { ReasoningSlider } from './ReasoningSlider';
import { useSettingsStore } from '../../stores/settingsStore';
import { getWebSocket } from '../../hooks/useWebSocket';

function update(path: string, value: unknown) {
  useSettingsStore.getState().update(path, value);
  getWebSocket().updateSetting(path, value);
}

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div style={styles.overlay}>
      <div style={styles.panel}>
        <div style={styles.header}>
          <h2 style={styles.title}>Settings</h2>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Model</h3>
          <ModelSelector />
          <ReasoningSlider />
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>UI</h3>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={settings.ui.show_reasoning}
              onChange={(e) => update('ui.show_reasoning', e.target.checked)}
            />
            Show reasoning
          </label>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={settings.ui.show_tool_calls}
              onChange={(e) => update('ui.show_tool_calls', e.target.checked)}
            />
            Show tool calls
          </label>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Voice</h3>
          <label style={styles.label}>
            STT Model:
            <select
              value={settings.voice.stt.model_size}
              onChange={(e) => update('voice.stt.model_size', e.target.value)}
              style={styles.select}
            >
              <option value="tiny">Tiny (fast)</option>
              <option value="small">Small (balanced)</option>
              <option value="medium">Medium (accurate)</option>
            </select>
          </label>
          <label style={styles.label}>
            TTS Voice:
            <select
              value={settings.voice.tts.voice}
              onChange={(e) => update('voice.tts.voice', e.target.value)}
              style={styles.select}
            >
              <option value="en-US-JennyNeural">Jenny (US)</option>
              <option value="en-US-GuyNeural">Guy (US)</option>
              <option value="en-GB-SoniaNeural">Sonia (UK)</option>
            </select>
          </label>
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  panel: {
    backgroundColor: '#1a1a2e',
    border: '1px solid #2a2a4a',
    borderRadius: 16,
    padding: 24,
    width: 480,
    maxHeight: '80vh',
    overflow: 'auto',
    color: '#e0e0e0',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  title: { margin: 0, fontSize: 20, fontWeight: 700 },
  closeBtn: {
    backgroundColor: 'transparent',
    color: '#9ca3af',
    border: 'none',
    cursor: 'pointer',
    fontSize: 18,
  },
  section: { marginBottom: 20 },
  sectionTitle: { fontSize: 14, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', margin: '0 0 12px 0' },
  label: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    marginBottom: 8,
    color: '#d1d5db',
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
