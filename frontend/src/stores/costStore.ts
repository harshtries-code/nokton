import { create } from 'zustand';

export interface CostSummary {
  input_tokens: number;
  output_tokens: number;
  reasoning_tokens?: number;
  total_tokens?: number;
  cost_usd: number;
}

interface CostState {
  session: CostSummary;
  total: CostSummary;
  setSession: (s: CostSummary) => void;
  setTotal: (s: CostSummary) => void;
  reset: () => void;
}

const empty: CostSummary = {
  input_tokens: 0,
  output_tokens: 0,
  reasoning_tokens: 0,
  total_tokens: 0,
  cost_usd: 0,
};

export const useCostStore = create<CostState>((set) => ({
  session: { ...empty },
  total: { ...empty },
  setSession: (s) => set({ session: s }),
  setTotal: (s) => set({ total: s }),
  reset: () => set({ session: { ...empty }, total: { ...empty } }),
}));
