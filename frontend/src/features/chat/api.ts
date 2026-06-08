import type { Conversation, ConversationDetail } from './types';

import { API_BASE, getAuthHeaders } from '../../lib/api';

// ── Types ─────────────────────────────────────────────────────────────────

export interface ModelInfo {
  id: string;
  display_name: string;
  provider: string;
  description: string;
  context_window: number;
}

// ── Fetch available models ────────────────────────────────────────────────

export async function fetchModels(): Promise<ModelInfo[]> {
  const res = await fetch(`${API_BASE}/models`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch models');
  return res.json();
}

// ── Non-streaming ask ─────────────────────────────────────────────────────

export async function askQuestion(
  question: string,
  modelId?: string,
  userId?: string,
  workspaceId?: string,
  conversationId?: string,
): Promise<{ answer: string; model: string; conversation_id: string | null }> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      question,
      model_id: modelId,
      user_id: userId,
      workspace_id: workspaceId,
      conversation_id: conversationId,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Server error' }));
    throw new Error(error.detail || 'Failed to get response');
  }

  return res.json();
}

// ── Streaming ask (SSE) ──────────────────────────────────────────────────

export async function askQuestionStream(
  question: string,
  onChunk: (text: string, model: string, conversationId?: string) => void,
  modelId?: string,
  userId?: string,
  workspaceId?: string,
  conversationId?: string,
  messages?: Array<{ role: string; content: string }>,
): Promise<void> {
  const res = await fetch(`${API_BASE}/ask/stream`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Accept': 'text/event-stream' },
    body: JSON.stringify({
      question,
      model_id: modelId,
      user_id: userId,
      workspace_id: workspaceId,
      conversation_id: conversationId,
      messages: messages || [],
    }),
  });

  if (!res.ok) {
    throw new Error('Failed to start stream');
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error('No readable stream');

  const decoder = new TextDecoder('utf-8');
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split(/\r?\n\r?\n/);
    buffer = parts.pop() || '';

    for (const part of parts) {
      const lines = part.split(/\r?\n/);
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.slice(6).trim();
          if (dataStr) {
            try {
              const data = JSON.parse(dataStr);
              if (data.text || data.model) {
                onChunk(
                  data.text || '',
                  data.model || '',
                  data.conversation_id || undefined,
                );
              }
            } catch (e) {
              console.error('Failed to parse SSE line', e);
            }
          }
        }
      }
    }
  }
}

// ── Conversation CRUD ─────────────────────────────────────────────────────

export async function fetchConversations(workspaceId: string): Promise<Conversation[]> {
  const res = await fetch(`${API_BASE}/conversations?workspace_id=${encodeURIComponent(workspaceId)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch conversations');
  return res.json();
}

export async function fetchConversationDetail(conversationId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch conversation');
  return res.json();
}

export async function renameConversation(conversationId: string, title: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to rename conversation');
  return res.json();
}

export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/conversations/${encodeURIComponent(conversationId)}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to delete' }));
    throw new Error(error.detail || 'Failed to delete conversation');
  }
}

// ── Workflows (Level 5) ───────────────────────────────────────────────────

export interface ToolCall {
  tool: string;
  input: string;
  output: string;
}

export interface WorkflowSubmitResponse {
  workflow_id: string;
  status: string;
}

export interface WorkflowStatusResponse {
  workflow_id: string;
  status: 'QUEUED' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  question: string;
  answer: string | null;
  tool_calls: ToolCall[] | null;
  created_at: string;
  updated_at: string;
}

export async function submitWorkflow(
  question: string,
  workspaceId: string,
): Promise<WorkflowSubmitResponse> {
  const res = await fetch(`${API_BASE}/workflows/submit`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ question, workspace_id: workspaceId }),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to submit workflow' }));
    throw new Error(error.detail || 'Failed to submit research task');
  }
  return res.json();
}

export async function getWorkflowStatus(workflowId: string): Promise<WorkflowStatusResponse> {
  const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/status`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to get workflow status');
  return res.json();
}

export async function cancelWorkflow(workflowId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/cancel`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to cancel workflow');
}

export async function streamWorkflowStatus(
  workflowId: string,
  onEvent: (data: WorkflowStatusResponse) => void
): Promise<() => void> {
  const abortController = new AbortController();
  
  const connect = async () => {
    try {
      const res = await fetch(`${API_BASE}/workflows/${encodeURIComponent(workflowId)}/stream`, {
        headers: { ...getAuthHeaders(), 'Accept': 'text/event-stream' },
        signal: abortController.signal
      });
      
      if (!res.ok) throw new Error('Failed to connect to stream');
      
      const reader = res.body?.getReader();
      if (!reader) throw new Error('No readable stream');
      
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() || '';
        
        for (const part of parts) {
          const lines = part.split(/\r?\n/);
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.slice(6).trim();
              if (dataStr) {
                try {
                  const data = JSON.parse(dataStr);
                  onEvent(data);
                } catch (e) {
                  console.error('Failed to parse SSE line', e);
                }
              }
            }
          }
        }
      }
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        console.error('SSE Error:', e);
      }
    }
  };
  
  connect();
  
  return () => abortController.abort();
}

export async function listWorkflows(workspaceId?: string): Promise<WorkflowStatusResponse[]> {
  const url = workspaceId
    ? `${API_BASE}/workflows?workspace_id=${encodeURIComponent(workspaceId)}`
    : `${API_BASE}/workflows`;
  const res = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to list workflows');
  return res.json();
}
