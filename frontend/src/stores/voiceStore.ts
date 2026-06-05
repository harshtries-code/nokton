import { create } from 'zustand';

type VoiceStateType = 'idle' | 'listening' | 'speaking' | 'thinking' | 'error';

interface VoiceState {
  state: VoiceStateType;
  setState: (s: VoiceStateType) => void;
  wakeEnabled: boolean;
  setWakeEnabled: (v: boolean) => void;
}

export const useVoiceStore = create<VoiceState>((set) => ({
  state: 'idle',
  setState: (s) => set({ state: s }),
  wakeEnabled: false,
  setWakeEnabled: (v) => set({ wakeEnabled: v }),
}));
