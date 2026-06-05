import { useEffect } from 'react';
import { useSettingsStore } from '../stores/settingsStore';
import { getWebSocket } from './useWebSocket';

export function useSettings() {
  const store = useSettingsStore();

  useEffect(() => {
    store.load();
  }, []);

  const updateModel = (provider: string, model: string, reasoning_effort?: string) => {
    store.update('model.provider', provider);
    store.update('model.model', model);
    if (reasoning_effort) store.update('model.reasoning_effort', reasoning_effort);
    getWebSocket().setModel(provider, model, reasoning_effort);
  };

  return { settings: store.settings, updateModel };
}
