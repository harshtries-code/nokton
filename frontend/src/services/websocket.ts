import { StreamEvent } from '../types/messages';

export type WSHandler = (event: StreamEvent) => void;

export class NoktonWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<WSHandler>> = new Map();
  private connected = false;
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private intentionalClose = false;

  constructor(url = 'ws://localhost:8765/ws') {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.connected = true;
      this.reconnectDelay = 1000;
      this.intentionalClose = false;
      this.emit('connected', { type: 'connected' });
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StreamEvent;
        this.emit(data.type, data);
      } catch {}
    };

    this.ws.onclose = () => {
      this.connected = false;
      this.emit('disconnected', { type: 'disconnected' });
      if (!this.intentionalClose) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      this.emit('error', { type: 'error', error: 'WebSocket error' });
    };
  }

  disconnect() {
    this.intentionalClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }

  private scheduleReconnect() {
    if (this.reconnectTimer) return;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
      this.connect();
    }, this.reconnectDelay);
  }

  send(data: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  sendMessage(text: string, images?: string[]) {
    this.send({ type: 'user_message', text, images: images || [] });
  }

  cancel() {
    this.send({ type: 'cancel' });
  }

  updateSetting(key: string, value: unknown) {
    this.send({ type: 'settings_update', key, value });
  }

  setApiKey(provider: string, apiKey: string) {
    this.send({ type: 'set_api_key', provider, api_key: apiKey });
  }

  confirmTool(callId: string, approved: boolean, toolName?: string, args?: Record<string, unknown>) {
    this.send({ type: 'confirm_tool', call_id: callId, approved, tool_name: toolName, args });
  }

  setModel(provider: string, model: string, reasoning_effort?: string) {
    this.send({ type: 'set_model', provider, model, reasoning_effort });
  }

  getModels() {
    this.send({ type: 'get_models' });
  }

  voiceToggle(enabled: boolean) {
    this.send({ type: 'voice_toggle', enabled });
  }

  newConversation() {
    this.send({ type: 'new_conversation' });
  }

  loadConversation(conversationId: string) {
    this.send({ type: 'load_conversation', conversation_id: conversationId });
  }

  listConversations() {
    this.send({ type: 'list_conversations' });
  }

  on(event: string, handler: WSHandler) {
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
  }

  off(event: string, handler?: WSHandler) {
    if (!handler) {
      this.handlers.delete(event);
      return;
    }
    this.handlers.get(event)?.delete(handler);
  }

  isConnected() {
    return this.connected;
  }

  private emit(type: string, event: StreamEvent) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      for (const h of handlers) {
        try { h(event); } catch {}
      }
    }

    const wildcard = this.handlers.get('*');
    if (wildcard) {
      for (const h of wildcard) {
        try { h(event); } catch {}
      }
    }
  }
}
