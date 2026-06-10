import React, { useState, useEffect } from 'react';
import { getWebSocket } from '../../hooks/useWebSocket';
import { useSettingsStore } from '../../stores/settingsStore';

interface OnboardingProps {
  onComplete: () => void;
}

export function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState(0); // 0: Boot sequence, 1: Key config, 2: Model & Personality, 3: Syncing
  const [bootLog, setBootLog] = useState<string[]>([]);
  const [apiKey, setApiKey] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('openrouter');
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [personality, setPersonality] = useState('nokton');
  const [models, setModels] = useState<{ id: string; name: string }[]>([]);
  const [selectedModel, setSelectedModel] = useState('');

  // 1. Boot text animation
  useEffect(() => {
    if (step !== 0) return;

    const logs = [
      'SYSTEM SHUTDOWN DETECTED IN LAST SESSION...',
      'BOOTING NOKTON CORE ENGINE v0.1.0...',
      'CHECKING SYSTEM INTEGRITY... OK',
      'INITIALIZING PY AUDIO HOST STREAM... OK',
      'LOADING EDGE_TTS SYNTHESIZER... OK',
      'RESOLVING LOCAL COGNITIVE CONFIGURATION...',
      'WARNING: NO API CREDENTIALS FOUND!',
      'REDIRECTING TO SYSTEM COGNITIVE ONBOARDING...',
    ];

    let currentLogIndex = 0;
    const interval = setInterval(() => {
      if (currentLogIndex < logs.length) {
        setBootLog((prev) => [...prev, `[SYS] ${logs[currentLogIndex]}`]);
        currentLogIndex++;
      } else {
        clearInterval(interval);
        setTimeout(() => setStep(1), 1000);
      }
    }, 450);

    return () => clearInterval(interval);
  }, [step]);

  // 2. Validate API key
  const handleValidate = async () => {
    if (!apiKey.trim()) {
      setValidationError('Please enter a valid API key.');
      return;
    }

    setIsValidating(true);
    setValidationError('');

    try {
      // Send key save via REST API or WebSocket
      const resp = await fetch('http://localhost:8765/api/api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          provider: selectedProvider,
          api_key: apiKey.trim(),
        }),
      });

      if (resp.ok) {
        // Fetch models for this provider
        const modelsResp = await fetch('http://localhost:8765/api/models');
        if (modelsResp.ok) {
          const data = await modelsResp.json();
          const provData = data.providers.find((p: any) => p.id === selectedProvider);
          if (provData && provData.models && provData.models.length > 0) {
            setModels(provData.models);
            // Default to free flash model if it exists
            const freeFlash = provData.models.find((m: any) => m.id.includes('v4-flash') || m.id.includes('flash'));
            setSelectedModel(freeFlash ? freeFlash.id : provData.models[0].id);
          } else {
            // Fallbacks
            if (selectedProvider === 'openrouter') {
              setModels([
                { id: 'deepseek/deepseek-v4-flash:free', name: 'DeepSeek V4 Flash (Free)' },
                { id: 'google/gemma-3-27b-it:free', name: 'Gemma 3 27B IT (Free)' },
              ]);
              setSelectedModel('deepseek/deepseek-v4-flash:free');
            }
          }
        }
        setStep(2);
      } else {
        setValidationError('Validation failed. Please check your key.');
      }
    } catch (e) {
      setValidationError('Could not connect to backend server.');
    } finally {
      setIsValidating(false);
    }
  };

  const handleSkip = () => {
    // Skip key validation (runs on mock/fallback models)
    if (selectedProvider === 'openrouter') {
      setModels([
        { id: 'deepseek/deepseek-v4-flash:free', name: 'DeepSeek V4 Flash (Free)' },
        { id: 'google/gemma-3-27b-it:free', name: 'Gemma 3 27B IT (Free)' },
      ]);
      setSelectedModel('deepseek/deepseek-v4-flash:free');
    } else {
      setModels([{ id: 'mock-model', name: 'Offline Mock Model' }]);
      setSelectedModel('mock-model');
    }
    setStep(2);
  };

  // 3. Save model & personality and complete onboarding
  const handleFinalize = async () => {
    setStep(3);

    // Save configurations
    try {
      const store = useSettingsStore.getState();
      
      // Update ui.personality
      store.update('ui.personality', personality);
      // Update model settings
      store.update('model.provider', selectedProvider);
      store.update('model.model', selectedModel);

      // Send to backend
      const ws = getWebSocket();
      ws.updateSetting('ui.personality', personality);
      ws.setModel(selectedProvider, selectedModel);

      // Let backend process it
      setTimeout(() => {
        onComplete();
      }, 1500);
    } catch (e) {
      onComplete();
    }
  };

  return (
    <div style={styles.fullscreen}>
      <div style={styles.matrixBg} />
      
      <div style={styles.card}>
        <div style={styles.scanline} />
        
        {step === 0 && (
          <div style={styles.consoleBox}>
            <div style={styles.header}>NOKTON OS BOOT SEQUENCE</div>
            <div style={styles.logs}>
              {bootLog.map((log, idx) => (
                <div key={idx} style={styles.logLine}>{log}</div>
              ))}
              <div style={styles.cursor} />
            </div>
          </div>
        )}

        {step === 1 && (
          <div style={styles.onboardingStep}>
            <h1 style={styles.title}>COGNITIVE LINK SETTINGS</h1>
            <p style={styles.desc}>
              Please supply an API Key. We recommend <strong style={{color: '#00ff66'}}>OpenRouter</strong> for high-quality free models like DeepSeek & Gemma 3.
            </p>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>PROVIDER</label>
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                style={styles.select}
              >
                <option value="openrouter">OpenRouter (Recommended)</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="deepseek">DeepSeek</option>
                <option value="groq">Groq</option>
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>API KEY</label>
              <input
                type="password"
                placeholder={`Paste your ${selectedProvider} API key here...`}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                style={styles.input}
              />
            </div>

            {validationError && <div style={styles.errorText}>{validationError}</div>}

            <div style={styles.btnRow}>
              <button
                style={styles.skipBtn}
                onClick={handleSkip}
                disabled={isValidating}
              >
                SKIP (DEMO MODE)
              </button>
              <button
                style={styles.primaryBtn}
                onClick={handleValidate}
                disabled={isValidating}
              >
                {isValidating ? 'VALIDATING LINK...' : 'ESTABLISH COGNITIVE LINK'}
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div style={styles.onboardingStep}>
            <h1 style={styles.title}>COGNITIVE TUNING</h1>
            <p style={styles.desc}>
              Configure your assistant's primary personality profile and core model engine.
            </p>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>COGNITIVE CORE MODEL</label>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                style={styles.select}
              >
                {models.map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formLabel}>PERSONALITY PROFILE</label>
              <select
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
                style={styles.select}
              >
                <option value="nokton">Nokton (Base AI Desktop Companion)</option>
                <option value="butler">Alfred (Sincere British Butler)</option>
                <option value="overlord">HAL 9000 (Sarcastic Cybernetic System)</option>
              </select>
            </div>

            <button style={styles.glowingBtn} onClick={handleFinalize}>
              INITIALIZE COGNITIVE UPLINK
            </button>
          </div>
        )}

        {step === 3 && (
          <div style={styles.syncingBox}>
            <div style={styles.spinner} />
            <div style={styles.syncText}>SYNCING COGNITIVE MATRIX...</div>
            <div style={styles.subSyncText}>Calibrating voice channels & core neural weights</div>
          </div>
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  fullscreen: {
    position: 'fixed',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: '#05050a',
    color: '#00ff66',
    fontFamily: '"Courier New", Courier, monospace',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    overflow: 'hidden',
  },
  matrixBg: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundImage: 'linear-gradient(rgba(0, 255, 102, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 255, 102, 0.03) 1px, transparent 1px)',
    backgroundSize: '20px 20px',
    zIndex: 1,
  },
  card: {
    position: 'relative',
    width: 600,
    minHeight: 400,
    backgroundColor: '#0a0a14',
    border: '2px solid #00ff66',
    boxShadow: '0 0 25px rgba(0, 255, 102, 0.2)',
    borderRadius: 8,
    padding: 36,
    zIndex: 2,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  scanline: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    background: 'linear-gradient(rgba(18, 16, 16, 0) 50%, rgba(0, 0, 0, 0.25) 50%), linear-gradient(90deg, rgba(255, 0, 0, 0.06), rgba(0, 255, 0, 0.02), rgba(0, 0, 255, 0.06))',
    backgroundSize: '100% 4px, 6px 100%',
    pointerEvents: 'none',
  },
  consoleBox: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
  },
  header: {
    fontSize: 16,
    fontWeight: 700,
    borderBottom: '1px solid #00ff66',
    paddingBottom: 8,
    marginBottom: 16,
    letterSpacing: 2,
  },
  logs: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
    fontSize: 13,
  },
  logLine: {
    whiteSpace: 'pre-wrap',
  },
  cursor: {
    width: 8,
    height: 15,
    backgroundColor: '#00ff66',
    animation: 'pulse 1s infinite',
    marginTop: 8,
  },
  onboardingStep: {
    display: 'flex',
    flexDirection: 'column',
    flex: 1,
  },
  title: {
    fontSize: 22,
    fontWeight: 700,
    color: '#00ff66',
    marginBottom: 8,
    letterSpacing: 2,
    textAlign: 'center',
    textShadow: '0 0 8px rgba(0, 255, 102, 0.4)',
  },
  desc: {
    fontSize: 13,
    color: '#8c9c8c',
    lineHeight: 1.5,
    marginBottom: 24,
    textAlign: 'center',
  },
  formGroup: {
    marginBottom: 20,
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  formLabel: {
    fontSize: 12,
    fontWeight: 700,
    letterSpacing: 1.5,
  },
  select: {
    backgroundColor: '#0f0f1f',
    color: '#00ff66',
    border: '1px solid #00ff66',
    padding: '10px 14px',
    borderRadius: 4,
    fontSize: 14,
    fontFamily: 'inherit',
    outline: 'none',
    cursor: 'pointer',
  },
  input: {
    backgroundColor: '#0f0f1f',
    color: '#00ff66',
    border: '1px solid #00ff66',
    padding: '10px 14px',
    borderRadius: 4,
    fontSize: 14,
    fontFamily: 'inherit',
    outline: 'none',
  },
  errorText: {
    color: '#ff3333',
    fontSize: 12,
    marginBottom: 16,
    textAlign: 'center',
  },
  btnRow: {
    display: 'flex',
    gap: 16,
    marginTop: 'auto',
  },
  skipBtn: {
    backgroundColor: 'transparent',
    color: '#8c9c8c',
    border: '1px solid #8c9c8c',
    padding: '12px 20px',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 700,
    fontFamily: 'inherit',
    flex: 1,
  },
  primaryBtn: {
    backgroundColor: '#00ff66',
    color: '#0a0a14',
    border: '1px solid #00ff66',
    padding: '12px 20px',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 13,
    fontWeight: 700,
    fontFamily: 'inherit',
    flex: 1.5,
    boxShadow: '0 0 10px rgba(0, 255, 102, 0.3)',
  },
  glowingBtn: {
    backgroundColor: 'transparent',
    color: '#00ff66',
    border: '2px solid #00ff66',
    padding: '14px 24px',
    borderRadius: 4,
    cursor: 'pointer',
    fontSize: 15,
    fontWeight: 700,
    fontFamily: 'inherit',
    marginTop: 'auto',
    letterSpacing: 2,
    boxShadow: '0 0 15px rgba(0, 255, 102, 0.2)',
    transition: 'all 0.2s',
  },
  syncingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  spinner: {
    width: 50,
    height: 50,
    border: '3px solid rgba(0, 255, 102, 0.1)',
    borderTop: '3px solid #00ff66',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    marginBottom: 24,
  },
  syncText: {
    fontSize: 16,
    fontWeight: 700,
    letterSpacing: 2,
    marginBottom: 8,
  },
  subSyncText: {
    fontSize: 12,
    color: '#8c9c8c',
  },
};
