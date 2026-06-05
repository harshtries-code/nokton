import React, { useState } from 'react';
import { Sidebar } from './components/Layout/Sidebar';
import { MainView } from './components/Layout/MainView';
import { SettingsPanel } from './components/Settings/SettingsPanel';
import { VoiceIndicator } from './components/Voice/VoiceIndicator';
import { MicButton } from './components/Voice/MicButton';
import { useWebSocket } from './hooks/useWebSocket';
import { useConversation } from './hooks/useConversation';
import { useVoice } from './hooks/useVoice';
import { useSettingsStore } from './stores/settingsStore';

export default function App() {
  const [showSettings, setShowSettings] = useState(false);
  const { sendMessage, cancel } = useWebSocket();
  const { newConversation } = useConversation();
  const { toggleWake } = useVoice();
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div style={styles.app}>
      <Sidebar
        onNewChat={newConversation}
        onSettings={() => setShowSettings(true)}
      />
      <div style={styles.main}>
        <div style={styles.topBar}>
          <VoiceIndicator />
          <MicButton onToggle={toggleWake} />
        </div>
        <MainView onSendMessage={sendMessage} onCancel={cancel} />
      </div>
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  app: {
    display: 'flex',
    height: '100vh',
    backgroundColor: '#0f0f23',
    color: '#e0e0e0',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  main: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  topBar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 8,
    padding: '6px 16px',
    borderBottom: '1px solid #1f2937',
    backgroundColor: '#0f0f23',
  },
};
