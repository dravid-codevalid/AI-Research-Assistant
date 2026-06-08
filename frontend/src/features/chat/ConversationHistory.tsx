import { useRef, useEffect } from 'react';
import type { ChatMessage as ChatMessageType } from './types';
import ChatMessage from './ChatMessage';
import Skeleton from '../../components/Skeleton/Skeleton';

interface ConversationHistoryProps {
  messages: ChatMessageType[];
  isLoading: boolean;
  error: string | null;
}

export default function ConversationHistory({
  messages,
  isLoading,
  error,
}: ConversationHistoryProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Auto-scroll on new messages or loading */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const isEmpty = messages.length === 0 && !isLoading;

  return (
    <div className="flex flex-col gap-6 overflow-y-auto h-full p-6 scroll-smooth" id="conversation-history">
      {isEmpty ? (
        <div className="flex flex-col items-center justify-center h-full text-center max-w-lg mx-auto animate-[fade-in-up_0.8s_ease-out_forwards]">
          <span className="text-4xl mb-6 text-blue-500 opacity-80" aria-hidden="true">
            ✦
          </span>
          <h1 className="text-2xl font-semibold text-slate-100 mb-3 tracking-tight">
            Hello! I'm your AI Research Assistant.
          </h1>
          <p className="text-slate-400 leading-relaxed">
            Ask me anything — I'll help you explore ideas, summarize papers, and
            accelerate your research.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-8 max-w-4xl mx-auto w-full pb-8">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {isLoading && (!messages.length || messages[messages.length - 1].role !== 'assistant') && (
            <div className="flex gap-4 animate-[fade-in-up_0.4s_ease-out_forwards]">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/10 flex items-center justify-center text-blue-400 mt-1" aria-hidden="true">
                ✦
              </div>
              <div className="flex-1 max-w-[80%] bg-slate-900/50 border border-slate-800 rounded-2xl p-5 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
                <div className="flex gap-1.5 mb-4" aria-label="Assistant is typing">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <Skeleton lines={3} width="md" />
              </div>
            </div>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm" role="alert" id="chat-error">
              ⚠ {error}
            </div>
          )}
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
