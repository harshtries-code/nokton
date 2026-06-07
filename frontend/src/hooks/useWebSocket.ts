import { useEffect, useRef, useCallback } from 'react';
import { NoktonWebSocket, WSHandler } from '../services/websocket';
import { useConversationStore } from '../stores/conversationStore';
import { useVoiceStore } from '../stores/voiceStore';
import { useCostStore } from '../stores/costStore';
import { Message } from '../types/messages';

let wsInstance: NoktonWebSocket | null = null;

export function getWebSocket() {
  if (!wsInstance) {
    wsInstance = new NoktonWebSocket();
    wsInstance.connect();
  }
  return wsInstance;
}

let handlersRegistered = false;

function registerGlobalHandlers(ws: NoktonWebSocket) {
  if (handlersRegistered) return;
  handlersRegistered = true;

  const store = useConversationStore.getState();

  ws.on('connected', () => {
    useConversationStore.getState().setAgentState('idle');
  });

  ws.on('assistant_delta', (event) => {
    const s = useConversationStore.getState();
    s.setStreaming(true);
    if (event.text) {
      s.appendToLastAssistant(event.text);
      s.setStreamingText(event.text);
    }
  });

  ws.on('reasoning_delta', (event) => {
    const s = useConversationStore.getState();
    if (event.text) {
      s.appendReasoning(event.text);
      s.setStreamingText(event.text);
    }
  });

  ws.on('assistant_done', () => {
    const s = useConversationStore.getState();
    s.setStreaming(false);
    s.setStreamingText('');
    s.setAgentState('idle');
    fetch('/api/cost')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.session) useCostStore.getState().setSession(data.session);
        if (data && data.total) useCostStore.getState().setTotal(data.total);
      })
      .catch(() => {});
  });

  ws.on('tool_call', (event) => {
    useConversationStore.getState().addPendingToolCall({
      id: event.id || '',
      name: event.name || '',
      args: event.args || {},
      requires_confirm: event.requires_confirm || false,
    });
  });

  ws.on('tool_call_start', (event: any) => {
    useConversationStore.getState().addPendingToolCall({
      id: event.id || '',
      name: event.name || '',
      args: event.args || {},
      requires_confirm: false,
    });
  });

  ws.on('tool_result', (event) => {
    useConversationStore.getState().clearPendingToolCall(event.id || '');
  });

  ws.on('tool_error', (event) => {
    useConversationStore.getState().clearPendingToolCall(event.id || '');
  });

  ws.on('interrupted', () => {
    const s = useConversationStore.getState();
    s.setStreaming(false);
    s.setStreamingText('');
    s.setAgentState('idle');
  });

  ws.on('status', (event) => {
    if (event.state) useConversationStore.getState().setAgentState(event.state);
  });

  ws.on('error', (event) => {
    const s = useConversationStore.getState();
    s.setStreaming(false);
    s.setAgentState('error');
  });

  ws.on('voice_event', (event) => {
    if (event.state) {
      useVoiceStore.getState().setState(event.state as any);
    }
  });

  ws.on('conversation_created', (event: any) => {
    if (event.id) {
      useConversationStore.getState().setCurrentConversationId(event.id);
    }
  });

  ws.on('conversation_loaded', (event: any) => {
    if (event.id) {
      useConversationStore.getState().loadFromServer(event);
    }
  });

  ws.on('conversations_list', (event: any) => {
    if (Array.isArray(event.conversations)) {
      useConversationStore.getState().setConversations(event.conversations);
    }
  });

  ws.on('api_key_saved', () => {
    useConversationStore.getState().setAgentState('idle');
  });
}

export function useWebSocket() {
  const wsRef = useRef<NoktonWebSocket>(getWebSocket());

  useEffect(() => {
    const ws = wsRef.current;
    registerGlobalHandlers(ws);
    ws.connect();
  }, []);

  const sendMessage = useCallback((text: string, images?: string[]) => {
    const store = useConversationStore.getState();
    const msg: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: text,
      timestamp: new Date().toISOString(),
    };
    store.addMessage(msg);
    store.setAgentState('thinking');
    wsRef.current.sendMessage(text, images);
  }, []);

  const cancel = useCallback(() => {
    wsRef.current.cancel();
  }, []);

  const confirmTool = useCallback((callId: string, approved: boolean, toolName?: string, args?: Record<string, unknown>) => {
    wsRef.current.confirmTool(callId, approved, toolName, args);
    useConversationStore.getState().clearPendingToolCall(callId);
  }, []);

  return { ws: wsRef.current, sendMessage, cancel, confirmTool };
}
