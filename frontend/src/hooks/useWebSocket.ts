import { useEffect, useRef, useCallback } from 'react';
import { NoktonWebSocket } from '../services/websocket';
import { useConversationStore } from '../stores/conversationStore';
import { Message } from '../types/messages';

let wsInstance: NoktonWebSocket | null = null;

export function getWebSocket() {
  if (!wsInstance) {
    wsInstance = new NoktonWebSocket();
  }
  return wsInstance;
}

export function useWebSocket() {
  const wsRef = useRef<NoktonWebSocket>(getWebSocket());
  const store = useConversationStore();

  useEffect(() => {
    const ws = wsRef.current;

    ws.on('connected', () => {
      store.setAgentState('idle');
    });

    ws.on('assistant_delta', (event) => {
      store.setStreaming(true);
      if (event.text) {
        store.appendToLastAssistant(event.text);
        store.setStreamingText(event.text);
      }
    });

    ws.on('reasoning_delta', (event) => {
      if (event.text) {
        store.appendReasoning(event.text);
        store.setStreamingText(event.text);
      }
    });

    ws.on('assistant_done', () => {
      store.setStreaming(false);
      store.setStreamingText('');
      store.setAgentState('idle');
    });

    ws.on('tool_call', (event) => {
      store.addPendingToolCall({
        id: event.id || '',
        name: event.name || '',
        args: event.args || {},
        requires_confirm: event.requires_confirm || false,
      });
    });

    ws.on('tool_result', (event) => {
      store.clearPendingToolCall(event.id || '');
    });

    ws.on('tool_error', (event) => {
      store.clearPendingToolCall(event.id || '');
    });

    ws.on('interrupted', () => {
      store.setStreaming(false);
      store.setStreamingText('');
      store.setAgentState('idle');
    });

    ws.on('status', (event) => {
      if (event.state) store.setAgentState(event.state);
    });

    ws.on('error', (event) => {
      store.setStreaming(false);
      store.setAgentState('error');
    });

    ws.on('voice_event', (event) => {
      if (event.state) {
        const { useVoiceStore } = require('../stores/voiceStore');
        useVoiceStore.getState().setState(event.state as any);
      }
    });

    ws.connect();

    return () => {
      ws.off('connected');
      ws.off('assistant_delta');
      ws.off('reasoning_delta');
      ws.off('assistant_done');
      ws.off('tool_call');
      ws.off('tool_result');
      ws.off('tool_error');
      ws.off('interrupted');
      ws.off('status');
      ws.off('error');
      ws.off('voice_event');
    };
  }, []);

  const sendMessage = useCallback((text: string, images?: string[]) => {
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
    store.clearPendingToolCall(callId);
  }, []);

  return { ws: wsRef.current, sendMessage, cancel, confirmTool };
}
