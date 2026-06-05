import { useCallback } from 'react';
import { useVoiceStore } from '../stores/voiceStore';
import { getWebSocket } from './useWebSocket';

export function useVoice() {
  const store = useVoiceStore();

  const toggleWake = useCallback(() => {
    const next = !store.wakeEnabled;
    store.setWakeEnabled(next);
    getWebSocket().voiceToggle(next);
  }, [store.wakeEnabled]);

  return { voiceState: store.state, wakeEnabled: store.wakeEnabled, toggleWake };
}
