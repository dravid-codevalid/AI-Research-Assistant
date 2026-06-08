import { useState, useCallback, useRef } from 'react';
import type { ChatMessage } from '../types';
import { askQuestionStream, fetchConversationDetail } from '../api';

let nextId = 1;
function genId(): string {
  return `msg-${nextId++}-${Date.now()}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  // Track current messages so the stream callback can update it without closure issues
  const messagesRef = useRef<ChatMessage[]>([]);
  messagesRef.current = messages;

  const loadConversation = useCallback(async (convId: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const detail = await fetchConversationDetail(convId);
      setConversationId(convId);
      setMessages(
        detail.messages.map((m) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          model: m.model || undefined,
          timestamp: m.created_at ? new Date(m.created_at) : new Date(),
          isGenerating: false,
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
    async (
      question: string,
      modelId?: string,
      userId?: string,
      workspaceId?: string,
    ) => {
      const trimmed = question.trim();
      if (!trimmed) return;

      const userMsg: ChatMessage = {
        id: genId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setIsLoading(true);
      setError(null);

      const assistantId = genId();
      let createdAssistantMsg = false;

      // Build history from current messages for hybrid fallback
      const currentMessages = messagesRef.current;
      const historyMessages = currentMessages
        .filter((m) => !m.isGenerating)
        .map((m) => ({ role: m.role, content: m.content }));

      try {
        await askQuestionStream(
          trimmed,
          (text, model, newConversationId) => {
            // Capture conversation ID from first chunk
            if (newConversationId && !conversationId) {
              setConversationId(newConversationId);
            }

            if (!createdAssistantMsg) {
              createdAssistantMsg = true;
              setMessages((prev) => [
                ...prev,
                {
                  id: assistantId,
                  role: 'assistant',
                  content: text,
                  model: model,
                  timestamp: new Date(),
                  isGenerating: true,
                },
              ]);
            } else {
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === assistantId
                    ? {
                        ...msg,
                        content: msg.content + text,
                        model: model || msg.model,
                      }
                    : msg,
                ),
              );
            }
          },
          modelId,
          userId,
          workspaceId,
          conversationId || undefined,
          historyMessages,
        );
      } catch (err) {
        const message =
          err instanceof Error ? err.message : 'An unexpected error occurred';
        setError(message);
      } finally {
        // Stream finished or errored — remove the generating flag
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId ? { ...msg, isGenerating: false } : msg,
          ),
        );
        setIsLoading(false);
      }
    },
    [conversationId],
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

  return {
    messages,
    isLoading,
    error,
    conversationId,
    sendMessage,
    clearChat,
    loadConversation,
    startNewConversation,
    setConversationId,
  };
}
