import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Layout/Sidebar';
import { MainView } from './components/Layout/MainView';
import { SettingsPanel } from './components/Settings/SettingsPanel';
import { Onboarding } from './components/Settings/Onboarding';
import { NeuralCore } from './components/Voice/NeuralCore';
import { CostBadge } from './components/Layout/CostBadge';
import { useWebSocket } from './hooks/useWebSocket';
import { useConversation } from './hooks/useConversation';
import { useVoice } from './hooks/useVoice';
import { useSettingsStore } from './stores/settingsStore';
import { useVoiceStore } from './stores/voiceStore';
import { useConversationStore } from './stores/conversationStore';

export default function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [showLeftSidebar, setShowLeftSidebar] = useState(false);
  const [showChatLog, setShowChatLog] = useState(false);
  const [inputText, setInputText] = useState('');
  const [isLoaded, setIsLoaded] = useState(false);
  const [onboardingComplete, setOnboardingComplete] = useState(false);

  const { ws, sendMessage, cancel } = useWebSocket();
  const { newConversation } = useConversation();
  const { toggleWake } = useVoice();

  const settings = useSettingsStore((s) => s.settings);
  const voiceState = useVoiceStore((s) => s.state);
  const wakeEnabled = useVoiceStore((s) => s.wakeEnabled);
  const agentState = useConversationStore((s) => s.agentState);
  const isStreaming = useConversationStore((s) => s.isStreaming);
  const streamingText = useConversationStore((s) => s.streamingText);
  const messages = useConversationStore((s) => s.messages);
  const lastError = useConversationStore((s) => s.lastError);

  useEffect(() => {
    // Load config on mount
    useSettingsStore.getState().load().then(() => {
      setIsLoaded(true);
    });
  }, []);

  // Determine if onboarding is required (no API keys configured)
  const providersDict = settings.providers || {};
  const hasAnyKey = Object.values(providersDict).some(
    (prov: any) => prov.api_key && prov.api_key.trim() !== ''
  );

  const showOnboarding = isLoaded && !hasAnyKey && !onboardingComplete;

  const handleSend = () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;
    sendMessage(trimmed);
    setInputText('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePersonalityChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const val = e.target.value;
    useSettingsStore.getState().update('ui.personality', val);
    ws.updateSetting('ui.personality', val);
  };

  if (!isLoaded) {
    return (
      <div style={styles.loaderScreen}>
        <div style={styles.loaderSpinner} />
        <div style={styles.loaderText}>CONNECTING TO COGNITIVE KERNEL...</div>
      </div>
    );
  }

  if (showOnboarding) {
    return <Onboarding onComplete={() => setOnboardingComplete(true)} />;
  }

  // Narration text — what the AI is saying/doing right now
  const lastMsg = messages[messages.length - 1];
  const narrationText = lastError
    ? `⚠ ${lastError}`
    : agentState === 'thinking'
    ? '⟳ Processing...'
    : isStreaming
    ? streamingText
    : lastMsg && lastMsg.role === 'assistant'
    ? lastMsg.content
    : '';
  const isError = !!lastError;

  return (
    <div style={styles.app}>

      {/* Left Sidebar Drawer */}
      {showLeftSidebar && (
        <div style={styles.sidebarWrapper}>
          <Sidebar
            onNewChat={() => {
              newConversation();
              setShowLeftSidebar(false);
            }}
            onSettings={() => setShowSettings(true)}
          />
        </div>
      )}

      {/* Main Visualizer Deck */}
      <div style={styles.deck}>
        {/* Top telemetry bar */}
        <div style={styles.telemetryBar}>
          <div style={styles.telemetryText}>
            NOKTON_SYS // STATE: <span style={styles.stateValue(voiceState)}>{voiceState.toUpperCase()}</span>
          </div>
          <CostBadge />
          <div style={styles.telemetryText}>
            CORE_MODEL: <span style={{ color: '#00d4ff' }}>{settings.model.model}</span>
          </div>
        </div>

        {/* Center Canvas Neural Core */}
        <div style={styles.centerStage}>
          <NeuralCore state={voiceState} />
        </div>

        {/* Narration Strip — merged output display */}
        {narrationText && (
          <div style={{
            ...styles.narrationStrip,
            ...(isError ? styles.narrationError : {}),
            ...(isStreaming ? styles.narrationStreaming : {}),
          }}>
            <div style={styles.narrationText}>{narrationText}</div>
          </div>
        )}

        {/* Bottom Cyber Deck Controls */}
        <div style={styles.controlDeck}>
          <div style={styles.btnRow}>
            {/* Mute button */}
            <button
              onClick={() => {
                ws.voiceToggle(!wakeEnabled);
                useVoiceStore.getState().setWakeEnabled(!wakeEnabled);
              }}
              style={wakeEnabled ? styles.muteBtnActive : styles.muteBtn}
              title={wakeEnabled ? 'Mute microphone' : 'Unmute microphone'}
            >
              {wakeEnabled ? '🎤 LIVE_MIC' : '🔇 MIC_MUTED'}
            </button>

            {/* Stop button */}
            <button
              onClick={cancel}
              style={styles.stopBtn}
              title="Abort cognitive task"
            >
              ■ ABORT
            </button>

            {/* Personality profile */}
            <div style={styles.selectWrapper}>
              <select
                value={settings.ui.personality || 'nokton'}
                onChange={handlePersonalityChange}
                style={styles.personalitySelect}
              >
                <option value="nokton">PROFILE: NOKTON</option>
                <option value="butler">PROFILE: BUTLER</option>
                <option value="overlord">PROFILE: OVERLORD</option>
              </select>
            </div>

            {/* Settings button */}
            <button
              onClick={() => setShowSettings(true)}
              style={showSettings ? styles.deckBtnActive : styles.deckBtn}
            >
              ⚙ SETTINGS
            </button>

            {/* Chat drawer toggle */}
            <button
              onClick={() => setShowChatLog(!showChatLog)}
              style={showChatLog ? styles.deckBtnActive : styles.deckBtn}
            >
              ⌨ CHAT_LOGS
            </button>
          </div>

          {/* Terminal Manual Input */}
          <div style={styles.terminalInputContainer}>
            <span style={styles.terminalPrompt}>NOKTON@SYS:~$</span>
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Inject manual directive..."
              style={styles.terminalInput}
            />
            <button onClick={handleSend} style={styles.terminalSendBtn}>
              ▶
            </button>
          </div>
        </div>
      </div>

      {/* Right Chat Log Slide-out Drawer */}
      {showChatLog && (
        <div style={styles.chatLogDrawer}>
          <div style={styles.drawerHeader}>
            <span style={styles.drawerTitle}>CHAT CONSOLE HISTORY</span>
            <button onClick={() => setShowChatLog(false)} style={styles.closeBtn}>
              ✕
            </button>
          </div>
          <div style={styles.drawerContent}>
            <MainView onSendMessage={sendMessage} onCancel={cancel} />
          </div>
        </div>
      )}

      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );
}

const styles: Record<string, any> = {
  app: {
    display: 'flex',
    height: '100vh',
    backgroundColor: '#0a0a0f',
    color: '#e2e8f0',
    fontFamily: '"Share Tech Mono", monospace, -apple-system, sans-serif',
    overflow: 'hidden',
    position: 'relative',
  },
  scanlines: {
    display: 'none', // Removed scanlines for cleaner look
  },
  loaderScreen: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0a0a0f',
    color: '#00d4ff',
    fontFamily: 'monospace',
  },
  loaderSpinner: {
    width: 40,
    height: 40,
    border: '3px solid rgba(0, 212, 255, 0.1)',
    borderTop: '3px solid #00d4ff',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: 16,
  },
  loaderText: {
    fontSize: 12,
    letterSpacing: 2,
    color: 'rgba(0, 212, 255, 0.6)',
  },
  sidebarWrapper: {
    position: 'absolute',
    left: 0,
    top: 0,
    bottom: 0,
    zIndex: 200,
    display: 'flex',
    boxShadow: '5px 0 15px rgba(0,0,0,0.5)',
  },
  deck: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    position: 'relative',
    zIndex: 10,
  },
  telemetryBar: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '8px 16px',
    borderBottom: '1px solid rgba(0, 212, 255, 0.12)',
    fontSize: 12,
    letterSpacing: 1.5,
    backgroundColor: 'rgba(8, 8, 18, 0.85)',
    backdropFilter: 'blur(10px)',
  },
  telemetryText: {
    color: 'rgba(0, 212, 255, 0.6)',
  },
  stateValue: (state: string) => {
    const colors: Record<string, string> = {
      idle: '#00d4ff',
      listening: '#00f0ff',
      speaking: '#a855f7',
      thinking: '#8b5cf6',
      error: '#ef4444',
    };
    return { color: colors[state] || '#00d4ff', fontWeight: 'bold' };
  },
  centerStage: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
    padding: 24,
  },
  narrationStrip: {
    padding: '8px 20px',
    backgroundColor: 'rgba(8, 8, 18, 0.7)',
    borderTop: '1px solid rgba(0, 212, 255, 0.06)',
    maxHeight: 80,
    overflowY: 'auto',
    flexShrink: 0,
  },
  narrationError: {
    borderTop: '1px solid rgba(239, 68, 68, 0.2)',
    backgroundColor: 'rgba(239, 68, 68, 0.05)',
  },
  narrationStreaming: {
    borderTop: '1px solid rgba(0, 212, 255, 0.15)',
  },
  narrationText: {
    fontSize: 13,
    color: 'rgba(226, 232, 240, 0.7)',
    lineHeight: 1.5,
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  controlDeck: {
    backgroundColor: 'rgba(8, 8, 18, 0.92)',
    borderTop: '1px solid rgba(0, 212, 255, 0.1)',
    padding: 16,
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
    backdropFilter: 'blur(10px)',
  },
  btnRow: {
    display: 'flex',
    gap: 12,
    flexWrap: 'wrap',
  },
  muteBtn: {
    backgroundColor: 'transparent',
    color: '#ef4444',
    border: '1px solid rgba(239, 68, 68, 0.4)',
    padding: '8px 16px',
    borderRadius: 6,
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 1,
    transition: 'all 0.2s ease',
  },
  muteBtnActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.15)',
    color: '#00d4ff',
    border: '1px solid #00d4ff',
    padding: '8px 16px',
    borderRadius: 6,
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 1,
    boxShadow: '0 0 12px rgba(0, 212, 255, 0.2)',
    transition: 'all 0.2s ease',
  },
  stopBtn: {
    backgroundColor: 'transparent',
    color: '#ef4444',
    border: '1px solid rgba(239, 68, 68, 0.4)',
    padding: '8px 16px',
    borderRadius: 6,
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 1,
    transition: 'all 0.2s ease',
  },
  deckBtn: {
    backgroundColor: 'transparent',
    color: 'rgba(0, 212, 255, 0.6)',
    border: '1px solid rgba(0, 212, 255, 0.2)',
    padding: '8px 16px',
    borderRadius: 6,
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    letterSpacing: 1,
    transition: 'all 0.2s ease',
  },
  deckBtnActive: {
    backgroundColor: 'rgba(0, 212, 255, 0.1)',
    color: '#00d4ff',
    border: '1px solid rgba(0, 212, 255, 0.4)',
    padding: '8px 16px',
    borderRadius: 6,
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: 13,
    letterSpacing: 1,
    transition: 'all 0.2s ease',
  },
  selectWrapper: {
    display: 'flex',
    alignItems: 'center',
  },
  personalitySelect: {
    backgroundColor: 'rgba(13, 17, 23, 0.9)',
    color: '#00d4ff',
    border: '1px solid rgba(0, 212, 255, 0.2)',
    padding: '8px 12px',
    borderRadius: 6,
    fontSize: 13,
    fontFamily: 'inherit',
    cursor: 'pointer',
    outline: 'none',
  },
  terminalInputContainer: {
    display: 'flex',
    alignItems: 'center',
    backgroundColor: 'rgba(10, 10, 15, 0.8)',
    border: '1px solid rgba(0, 212, 255, 0.25)',
    borderRadius: 8,
    padding: '8px 12px',
    boxShadow: 'inset 0 1px 3px rgba(0, 0, 0, 0.3)',
  },
  terminalPrompt: {
    color: '#00d4ff',
    marginRight: 12,
    fontSize: 14,
    fontWeight: 'bold',
    userSelect: 'none',
  },
  terminalInput: {
    flex: 1,
    backgroundColor: 'transparent',
    color: '#e2e8f0',
    border: 'none',
    outline: 'none',
    fontSize: 14,
    fontFamily: 'inherit',
  },
  terminalSendBtn: {
    backgroundColor: 'transparent',
    color: '#00d4ff',
    border: 'none',
    cursor: 'pointer',
    fontSize: 16,
    padding: '0 4px',
  },
  chatLogDrawer: {
    position: 'absolute',
    top: 0, right: 0, bottom: 0,
    width: 420,
    backgroundColor: 'rgba(10, 10, 18, 0.95)',
    borderLeft: '1px solid rgba(0, 212, 255, 0.15)',
    display: 'flex',
    flexDirection: 'column',
    zIndex: 150,
    boxShadow: '-5px 0 25px rgba(0, 0, 0, 0.5)',
    backdropFilter: 'blur(16px)',
  },
  drawerHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottom: '1px solid rgba(0, 212, 255, 0.1)',
  },
  drawerTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    letterSpacing: 1.5,
    color: '#00d4ff',
  },
  closeBtn: {
    backgroundColor: 'transparent',
    color: 'rgba(0, 212, 255, 0.6)',
    border: 'none',
    cursor: 'pointer',
    fontSize: 16,
  },
  drawerContent: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
};
