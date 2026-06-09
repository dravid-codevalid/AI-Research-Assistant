import { createContext, useContext, useState, useCallback, useRef, type ReactNode } from 'react';
import type { AgentMessage } from '../features/agent/types';
import { askAgentStream } from '../features/agent/api';
import { fetchConversationDetail } from '../features/chat/api';

interface AgentContextValue {
  messages: AgentMessage[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
  sendMessage: (question: string, userId?: string, workspaceId?: string) => Promise<void>;
  clearChat: () => void;
  loadConversation: (convId: string) => Promise<void>;
  startNewConversation: () => void;
}

const AgentContext = createContext<AgentContextValue | null>(null);

let nextId = 1;
function genId(): string {
  return `agent-msg-${nextId++}-${Date.now()}`;
}

export function AgentProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  // We keep a ref of the conversation ID so the stream callbacks can read it
  const conversationIdRef = useRef<string | null>(null);
  conversationIdRef.current = conversationId;

  const loadConversation = useCallback(async (convId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await fetchConversationDetail(convId);
      setConversationId(convId);
      setMessages(
        detail.messages.map((m) => ({
          id: m.id,
          role: m.role === 'user' ? 'user' : 'agent',
          content: m.content,
          model_used: m.model || undefined,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
          tool_calls: m.tool_calls || undefined,
        }))
      );
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to load conversation';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (question: string, userId?: string, workspaceId?: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      const userMsg: AgentMessage = {
        id: genId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      const agentId = genId();
      setMessages((prev) => [
        ...prev,
        {
          id: agentId,
          role: 'agent',
          content: '',
          timestamp: new Date(),
          isLoading: true,
        },
      ]);

      try {
        let textAccumulator = '';
        const thoughtsAccumulator: string[] = [];
        const toolCallsAccumulator: any[] = [];
        let modelUsedValue = '';

        await askAgentStream(
          trimmed,
          (event) => {
            if (event.event === 'conversation_id' && event.conversation_id) {
              setConversationId(event.conversation_id);
            } else if (event.event === 'thought' && event.text) {
              if (thoughtsAccumulator.length <= toolCallsAccumulator.length) {
                thoughtsAccumulator.push(event.text);
              } else {
                thoughtsAccumulator[thoughtsAccumulator.length - 1] += event.text;
              }
            } else if (event.event === 'tool_call') {
              toolCallsAccumulator.push({
                tool: event.tool,
                input: event.input,
                output: event.output,
              });
            } else if (event.event === 'token' && event.text) {
              textAccumulator += event.text;
              if (event.model_used) modelUsedValue = event.model_used;
            }

            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === agentId
                  ? {
                      ...msg,
                      content: textAccumulator,
                      tool_calls: [...toolCallsAccumulator],
                      thoughts: [...thoughtsAccumulator],
                      model_used: modelUsedValue || undefined,
                    }
                  : msg,
              ),
            );
          },
          userId,
          workspaceId,
          conversationIdRef.current || undefined,
        );

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === agentId
              ? {
                  ...msg,
                  isLoading: false,
                }
              : msg,
          ),
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(message);
        setMessages((prev) => prev.filter((msg) => msg.id !== agentId));
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  const startNewConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
  }, []);

  return (
    <AgentContext.Provider
      value={{
        messages,
        isLoading,
        error,
        conversationId,
        sendMessage,
        clearChat,
        loadConversation,
        startNewConversation,
      }}
    >
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent() {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error('useAgent must be used within AgentProvider');
  return ctx;
}
