import type { AgentResponse, AgentMemory } from './types';

import { API_BASE, getAuthHeaders } from '../../lib/api';

// ── Agent ask ────────────────────────────────────────────────────────────

export async function askAgent(
  question: string,
  userId?: string,
  workspaceId?: string,
): Promise<AgentResponse> {
  const res = await fetch(`${API_BASE}/agent/ask`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      question,
      user_id: userId,
      workspace_id: workspaceId,
    }),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Agent error' }));
    throw new Error(error.detail || 'Failed to get agent response');
  }

  return res.json();
}

export async function askAgentStream(
  question: string,
  onEvent: (event: {
    event: 'thought' | 'tool_call' | 'token' | 'done' | 'error';
    text?: string;
    tool?: string;
    input?: string;
    output?: string;
    model_used?: string;
  }) => void,
  userId?: string,
  workspaceId?: string,
): Promise<void> {
  const res = await fetch(`${API_BASE}/agent/ask/stream`, {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Accept': 'text/event-stream' },
    body: JSON.stringify({
      question,
      user_id: userId,
      workspace_id: workspaceId,
    }),
  });

  if (!res.ok) {
    throw new Error('Failed to start agent stream');
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
      if (part.startsWith('data: ')) {
        const dataStr = part.slice(6).trim();
        if (dataStr) {
          try {
            const data = JSON.parse(dataStr);
            onEvent(data);
          } catch (e) {
            console.error('Failed to parse agent SSE chunk', e);
          }
        }
      }
    }
  }
}

// ── Agent memory ─────────────────────────────────────────────────────────

export async function getAgentMemory(): Promise<AgentMemory> {
  const res = await fetch(`${API_BASE}/agent/memory`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch agent memory');
  return res.json();
}

export async function clearAgentMemory(): Promise<AgentMemory> {
  const res = await fetch(`${API_BASE}/agent/memory`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to clear agent memory');
  return res.json();
}

export interface ModelInfo {
  version: string;
  model_name: string;
  val_score: number | null;
  source: string;
}

export async function getAgentModelInfo(): Promise<ModelInfo> {
  const res = await fetch(`${API_BASE}/agent/model-info`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch agent model info');
  return res.json();
}

