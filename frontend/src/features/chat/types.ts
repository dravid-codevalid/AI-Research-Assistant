export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  model?: string;
  timestamp: Date;
  isGenerating?: boolean;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  created_by: string;
  title: string;
  created_at?: string;
  updated_at?: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: Array<{
    id: string;
    conversation_id: string;
    role: 'user' | 'assistant';
    content: string;
    model?: string;
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
    created_at?: string;
  }>;
}
