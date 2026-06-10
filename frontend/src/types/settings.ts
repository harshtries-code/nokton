export interface Settings {
  model: {
    provider: string;
    model: string;
    small_model: string;
    vision_model: string;
    reasoning_effort: string;
    temperature: number;
    max_tokens: number;
  };
  providers?: Record<string, {
    api_key?: string;
    base_url?: string;
  }>;
  voice: {
    wake_word: { enabled: boolean; sensitivity: number };
    stt: { engine: string; model_size: string; device: string };
    tts: { engine: string; voice: string; rate: string };
    vad: { threshold: number; silence_duration_ms: number };
  };
  ui: {
    theme: string;
    font_size: number;
    streaming_animation: boolean;
    show_reasoning: boolean;
    show_tool_calls: boolean;
    personality?: string;
  };
}
