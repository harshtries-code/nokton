export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: string;
  duration_ms?: number;
  requires_confirm?: boolean;
  approved?: boolean;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  reasoning?: string;
  tool_calls?: ToolCall[];
  timestamp: string;
}

export interface StreamEvent {
  type: string;
  text?: string;
  id?: string;
  name?: string;
  args?: Record<string, unknown>;
  output?: string;
  error?: string;
  state?: string;
  requires_confirm?: boolean;
  code?: string;
  message?: string;
  duration_ms?: number;
}
