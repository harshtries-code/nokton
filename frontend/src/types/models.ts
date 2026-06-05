export interface ModelCapabilities {
  vision: boolean;
  tool_calling: boolean;
  streaming: boolean;
  reasoning: boolean;
}

export interface ModelPricing {
  input_per_1m: number;
  output_per_1m: number;
  is_free: boolean;
}

export interface ModelInfo {
  id: string;
  name: string;
  context_window: number;
  max_output: number;
  capabilities: ModelCapabilities;
  pricing?: ModelPricing;
}

export interface ProviderInfo {
  id: string;
  name: string;
  requires_api_key: boolean;
  models: ModelInfo[];
}
