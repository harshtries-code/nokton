import React from 'react';
import { useVoiceStore } from '../../stores/voiceStore';

export function MicButton({ onToggle }: { onToggle: () => void }) {
  const wakeEnabled = useVoiceStore((s) => s.wakeEnabled);

  return (
    <button
      onClick={onToggle}
      style={{
        ...styles.button,
        backgroundColor: wakeEnabled ? '#7c3aed' : '#1f2937',
      }}
      title={wakeEnabled ? 'Disable wake word' : 'Enable wake word'}
    >
      🎤
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  button: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    border: 'none',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 14,
    color: '#fff',
  },
};
