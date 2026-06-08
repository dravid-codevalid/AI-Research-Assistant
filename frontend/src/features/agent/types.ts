export interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

export interface AgentMessage {
  id: string;
  role: 'user' | 'agent';
  content: string;
  tool_calls?: ToolCall[];
  model_used?: string;
  timestamp: Date;
  isLoading?: boolean;
  thoughts?: string[];
}

export interface AgentResponse {
  answer: string;
  tool_calls: ToolCall[];
  model_used: string | null;
  thoughts: string[];
}

export interface AgentMemory {
  memory: Record<string, string>;
}
