import { create } from 'zustand';
import { Settings } from '../types/settings';

const DEFAULT_SETTINGS: Settings = {
  model: {
    provider: 'openrouter',
    model: 'deepseek/deepseek-v4-flash:free',
    small_model: 'openrouter/gpt-oss-20b:free',
    vision_model: 'openrouter/google/gemma-3-27b-it:free',
    reasoning_effort: 'high',
    temperature: 0.7,
    max_tokens: 4096,
  },
  voice: {
    wake_word: { enabled: false, sensitivity: 0.7 },
    stt: { engine: 'faster-whisper', model_size: 'small', device: 'cpu' },
    tts: { engine: 'edge-tts', voice: 'en-US-JennyNeural', rate: '+0%' },
    vad: { threshold: 0.5, silence_duration_ms: 800 },
  },
  ui: {
    theme: 'dark',
    font_size: 14,
    streaming_animation: true,
    show_reasoning: false,
    show_tool_calls: true,
  },
};

interface SettingsState {
  settings: Settings;
  load: () => Promise<void>;
  update: (path: string, value: unknown) => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: DEFAULT_SETTINGS,

  load: async () => {
    try {
      const resp = await fetch('http://localhost:8765/api/settings');
      if (resp.ok) {
        const data = await resp.json();
        set({ settings: { ...DEFAULT_SETTINGS, ...data } });
      }
    } catch {}
  },

  update: (path, value) => set((s) => {
    const updated = JSON.parse(JSON.stringify(s.settings));
    const keys = path.split('.');
    let obj: any = updated;
    for (let i = 0; i < keys.length - 1; i++) obj = obj[keys[i]];
    obj[keys[keys.length - 1]] = value;
    return { settings: updated };
  }),
}));
