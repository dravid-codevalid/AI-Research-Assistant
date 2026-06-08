import { useState, useCallback } from 'react';
import type { AgentMessage } from '../types';
import { askAgentStream } from '../api';

let nextId = 1;
function genId(): string {
  return `agent-msg-${nextId++}-${Date.now()}`;
}

export function useAgent() {
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (question: string, userId?: string, workspaceId?: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      // Add user message
      const userMsg: AgentMessage = {
        id: genId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      // Add placeholder agent message
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
            if (event.event === 'thought' && event.text) {
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

            // Update the message state incrementally
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
        );

        // Turn off loading once complete
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

        // Remove the placeholder message on error
        setMessages((prev) => prev.filter((msg) => msg.id !== agentId));
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
  };
}
