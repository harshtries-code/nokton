import { StreamEvent } from '../types/messages';

export class NoktonWebSocket {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, (event: StreamEvent) => void> = new Map();
  private connected = false;

  constructor(url = 'ws://localhost:8765/ws') {
    this.url = url;
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.connected = true;
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
    };

    this.ws.onerror = (error) => {
      this.emit('error', { type: 'error', error: 'WebSocket error' });
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
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

  listConversations() {
    this.send({ type: 'list_conversations' });
  }

  on(event: string, handler: (event: StreamEvent) => void) {
    this.handlers.set(event, handler);
  }

  off(event: string) {
    this.handlers.delete(event);
  }

  isConnected() {
    return this.connected;
  }

  private emit(type: string, event: StreamEvent) {
    const handler = this.handlers.get(type);
    if (handler) handler(event);

    const wildcard = this.handlers.get('*');
    if (wildcard) wildcard(event);
  }
}
