import { create } from 'zustand';
import { Message, ToolCall } from '../types/messages';

interface ConversationState {
  messages: Message[];
  isStreaming: boolean;
  streamingText: string;
  streamingReasoning: string;
  agentState: string;
  pendingToolCalls: ToolCall[];
  addMessage: (msg: Message) => void;
  appendToLastAssistant: (text: string) => void;
  appendReasoning: (text: string) => void;
  setStreaming: (v: boolean) => void;
  setStreamingText: (t: string) => void;
  setAgentState: (s: string) => void;
  addPendingToolCall: (tc: ToolCall) => void;
  clearPendingToolCall: (id: string) => void;
  clearMessages: () => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingText: '',
  streamingReasoning: '',
  agentState: 'idle',
  pendingToolCalls: [],

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastAssistant: (text) => set((s) => {
    const msgs = [...s.messages];
    const last = msgs[msgs.length - 1];
    if (last && last.role === 'assistant') {
      msgs[msgs.length - 1] = { ...last, content: last.content + text };
    }
    return { messages: msgs };
  }),

  appendReasoning: (text) => set((s) => {
    const msgs = [...s.messages];
    const last = msgs[msgs.length - 1];
    if (last && last.role === 'assistant') {
      msgs[msgs.length - 1] = { ...last, reasoning: (last.reasoning || '') + text };
    }
    return { messages: msgs };
  }),

  setStreaming: (v) => set({ isStreaming: v }),
  setStreamingText: (t) => set({ streamingText: t }),
  setAgentState: (s) => set({ agentState: s }),

  addPendingToolCall: (tc) => set((s) => ({
    pendingToolCalls: [...s.pendingToolCalls, tc],
  })),

  clearPendingToolCall: (id) => set((s) => ({
    pendingToolCalls: s.pendingToolCalls.filter((t) => t.id !== id),
  })),

  clearMessages: () => set({
    messages: [],
    streamingText: '',
    streamingReasoning: '',
    pendingToolCalls: [],
  }),
}));
