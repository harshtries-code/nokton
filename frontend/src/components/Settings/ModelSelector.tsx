import React, { useEffect, useState } from 'react';
import { ProviderInfo } from '../../types/models';
import { getWebSocket } from '../../hooks/useWebSocket';
import { useSettingsStore } from '../../stores/settingsStore';

export function ModelSelector() {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const settings = useSettingsStore((s) => s.settings);

  useEffect(() => {
    const ws = getWebSocket();
    ws.on('models_list', (event: any) => {
      if (event.providers) setProviders(event.providers);
    });
    ws.getModels();
    return () => ws.off('models_list');
  }, []);

  const selectedProvider = settings.model.provider;
  const selectedModel = settings.model.model;
  const currentProvider = providers.find((p) => p.id === selectedProvider);
  const models = currentProvider?.models || [];

  return (
    <div style={styles.group}>
      <label style={styles.label}>
        Provider:
        <select
          value={selectedProvider}
          onChange={(e) => {
            const p = e.target.value;
            const newProvider = providers.find((pr) => pr.id === p);
            const firstModel = newProvider?.models[0]?.id || '';
            useSettingsStore.getState().update('model.provider', p);
            if (firstModel) useSettingsStore.getState().update('model.model', firstModel);
            getWebSocket().setModel(p, firstModel);
          }}
          style={styles.select}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </label>

      <label style={styles.label}>
        Model:
        <select
          value={selectedModel}
          onChange={(e) => {
            const m = e.target.value;
            useSettingsStore.getState().update('model.model', m);
            getWebSocket().setModel(selectedProvider, m);
          }}
          style={styles.select}
        >
          {models.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name} {m.capabilities?.reasoning ? '(reasoning)' : ''} {m.pricing?.is_free ? '(free)' : ''}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  group: { display: 'flex', flexDirection: 'column', gap: 8 },
  label: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontSize: 13,
    color: '#e2e8f0',
  },
  select: {
    flex: 1,
    backgroundColor: 'rgba(10, 10, 15, 0.8)',
    color: '#e2e8f0',
    border: '1px solid rgba(0, 212, 255, 0.15)',
    borderRadius: 6,
    padding: '6px 8px',
    fontSize: 13,
    fontFamily: 'inherit',
  },
};
