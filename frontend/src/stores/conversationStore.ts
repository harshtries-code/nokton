import { create } from 'zustand';
import { Message, ToolCall } from '../types/messages';

export interface ConversationSummary {
  id: string;
  title: string;
  message_count: number;
  updated_at: string;
}

interface ConversationState {
  messages: Message[];
  isStreaming: boolean;
  streamingText: string;
  streamingReasoning: string;
  agentState: string;
  pendingToolCalls: ToolCall[];
  conversations: ConversationSummary[];
  currentConversationId: string | null;
  lastError: string | null;
  addMessage: (msg: Message) => void;
  appendToLastAssistant: (text: string) => void;
  appendReasoning: (text: string) => void;
  setStreaming: (v: boolean) => void;
  setStreamingText: (t: string) => void;
  setAgentState: (s: string) => void;
  addPendingToolCall: (tc: ToolCall) => void;
  clearPendingToolCall: (id: string) => void;
  clearMessages: () => void;
  setConversations: (c: ConversationSummary[]) => void;
  setCurrentConversationId: (id: string | null) => void;
  loadFromServer: (conv: any) => void;
  setError: (err: string | null) => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  messages: [],
  isStreaming: false,
  streamingText: '',
  streamingReasoning: '',
  agentState: 'idle',
  pendingToolCalls: [],
  conversations: [],
  currentConversationId: null,
  lastError: null,

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastAssistant: (text) => set((s) => {
    const msgs = [...s.messages];
    const last = msgs[msgs.length - 1];
    if (last && last.role === 'assistant') {
      msgs[msgs.length - 1] = { ...last, content: last.content + text };
    } else {
      msgs.push({
        id: `msg_${Date.now()}`,
        role: 'assistant',
        content: text,
        timestamp: new Date().toISOString(),
      });
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

  setConversations: (conversations) => set({ conversations }),

  setCurrentConversationId: (id) => set({ currentConversationId: id }),

  loadFromServer: (conv) => set({
    currentConversationId: conv.id,
    messages: (conv.messages || []).map((m: any) => {
      let content = m.content;
      if (Array.isArray(content)) {
        content = content
          .map((p: any) => (typeof p === 'string' ? p : p?.text || ''))
          .filter(Boolean)
          .join(' ');
      }
      return {
        id: `msg_${m.timestamp || Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
        role: m.role,
        content: content || '',
        reasoning: m.reasoning,
        timestamp: m.timestamp,
        tool_calls: Array.isArray(m.tool_calls) ? m.tool_calls : undefined,
      };
    }),
    streamingText: '',
    streamingReasoning: '',
    pendingToolCalls: [],
  }),

  setError: (err) => set({ lastError: err }),
}));
