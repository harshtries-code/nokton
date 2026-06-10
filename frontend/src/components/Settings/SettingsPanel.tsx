import React from 'react';
import { ModelSelector } from './ModelSelector';
import { ReasoningSlider } from './ReasoningSlider';
import { ProviderSettings } from './ProviderSettings';
import { useSettingsStore } from '../../stores/settingsStore';
import { getWebSocket } from '../../hooks/useWebSocket';

function update(path: string, value: unknown) {
  useSettingsStore.getState().update(path, value);
  getWebSocket().updateSetting(path, value);
}

export function SettingsPanel({ onClose }: { onClose: () => void }) {
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.panel} onClick={(e) => e.stopPropagation()}>
        <div style={styles.header}>
          <h2 style={styles.title}>⚙ Settings</h2>
          <button style={styles.closeBtn} onClick={onClose}>✕</button>
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Model Configuration</h3>
          <ModelSelector />
          <ReasoningSlider />
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>API Keys</h3>
          <p style={styles.sectionHint}>Configure at least one provider. OpenRouter offers free models.</p>
          <ProviderSettings />
        </div>

        <div style={styles.section}>
          <h3 style={styles.sectionTitle}>Display</h3>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={settings.ui.show_reasoning}
              onChange={(e) => update('ui.show_reasoning', e.target.checked)}
              style={styles.checkbox}
            />
            Show reasoning traces
          </label>
          <label style={styles.label}>
            <input
              type="checkbox"
              checked={settings.ui.show_tool_calls}
              onChange={(e) => update('ui.show_tool_calls', e.target.checked)}
              style={styles.checkbox}
            />
            Show tool call details
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
    backgroundColor: 'rgba(0,0,0,0.7)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    backdropFilter: 'blur(4px)',
  },
  panel: {
    backgroundColor: 'rgba(10, 10, 18, 0.97)',
    border: '1px solid rgba(0, 212, 255, 0.2)',
    boxShadow: '0 8px 40px rgba(0, 0, 0, 0.6), 0 0 1px rgba(0, 212, 255, 0.3)',
    borderRadius: 12,
    padding: 24,
    width: 520,
    maxHeight: '85vh',
    overflow: 'auto',
    color: '#e2e8f0',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
    paddingBottom: 12,
    borderBottom: '1px solid rgba(0, 212, 255, 0.1)',
  },
  title: {
    margin: 0,
    fontSize: 18,
    fontWeight: 700,
    color: '#00d4ff',
    letterSpacing: 1,
  },
  closeBtn: {
    backgroundColor: 'transparent',
    color: 'rgba(226, 232, 240, 0.5)',
    border: 'none',
    cursor: 'pointer',
    fontSize: 18,
    padding: '4px 8px',
    borderRadius: 4,
    transition: 'color 0.2s',
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 600,
    color: 'rgba(0, 212, 255, 0.5)',
    textTransform: 'uppercase',
    letterSpacing: 1.5,
    margin: '0 0 10px 0',
  },
  sectionHint: {
    fontSize: 11,
    color: 'rgba(226, 232, 240, 0.35)',
    marginBottom: 10,
    marginTop: -4,
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    marginBottom: 8,
    color: '#d1d5db',
  },
  checkbox: {
    accentColor: '#00d4ff',
  },
  select: {
    backgroundColor: 'rgba(10, 10, 15, 0.8)',
    color: '#e2e8f0',
    border: '1px solid rgba(0, 212, 255, 0.15)',
    borderRadius: 6,
    padding: '5px 8px',
    fontSize: 13,
    fontFamily: 'inherit',
  },
};
