import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { AgentMessage as AgentMessageType } from './types';
import ToolCallCard from './ToolCallCard';

interface AgentMessageProps {
  message: AgentMessageType;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function AgentMessage({ message }: AgentMessageProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <article
        className="flex gap-4 flex-row-reverse animate-[fade-in-up_0.6s_cubic-bezier(0.32,0.72,0,1)_forwards]"
        id={`agent-message-${message.id}`}
      >
        <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium mt-1 bg-slate-800 text-slate-300" aria-hidden="true">
          U
        </div>
        <div className="flex flex-col gap-1.5 max-w-[80%] items-end">
          <div className="px-5 py-4 rounded-[1.5rem] rounded-tr-sm text-base leading-relaxed bg-indigo-900/30 border border-indigo-500/20 text-indigo-50 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
            {message.content}
          </div>
          <div className="flex items-center gap-3 px-2 text-xs text-slate-500 font-medium flex-row-reverse">
            <span>{formatTime(message.timestamp)}</span>
          </div>
        </div>
      </article>
    );
  }

  // Agent message with tool calls
  return (
    <article
      className="flex gap-4 animate-[fade-in-up_0.6s_cubic-bezier(0.32,0.72,0,1)_forwards]"
      id={`agent-message-${message.id}`}
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium mt-1 bg-emerald-500/10 text-emerald-400" aria-hidden="true">
        🤖
      </div>

      <div className="flex flex-col gap-2.5 max-w-[80%] items-start">
        {/* Loading state */}
        {message.isLoading && (
          <div className="px-5 py-4 rounded-[1.5rem] rounded-tl-sm bg-slate-900/50 border border-slate-800">
            <div className="flex items-center gap-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-emerald-400/60 rounded-full animate-[pulse_1.4s_ease-in-out_infinite]" />
                <span className="w-2 h-2 bg-emerald-400/60 rounded-full animate-[pulse_1.4s_ease-in-out_0.2s_infinite]" />
                <span className="w-2 h-2 bg-emerald-400/60 rounded-full animate-[pulse_1.4s_ease-in-out_0.4s_infinite]" />
              </div>
              <span className="text-sm text-slate-500 italic">
                Agent is thinking and using tools...
              </span>
            </div>
          </div>
        )}

        {/* Thoughts bubble */}
        {!message.isLoading && message.thoughts && message.thoughts.length > 0 && (
          <div className="px-5 py-3 rounded-2xl bg-slate-900/20 border border-slate-800/40 text-slate-400 text-xs italic space-y-1.5 w-full">
            <div className="font-semibold text-[10px] uppercase tracking-wider text-slate-500 not-italic flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
              Agent Thoughts
            </div>
            {message.thoughts.map((thought, idx) => (
              <p key={idx} className="leading-relaxed">
                {thought}
              </p>
            ))}
          </div>
        )}

        {/* Tool calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="w-full space-y-1.5">
            {message.tool_calls.map((tc, idx) => (
              <ToolCallCard key={idx} toolCall={tc} index={idx} />
            ))}
          </div>
        )}

        {/* Final answer */}
        {!message.isLoading && message.content && (
          <div className="px-5 py-4 rounded-[1.5rem] rounded-tl-sm text-base leading-relaxed bg-slate-900/50 border border-slate-800 text-slate-100 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
            <div className="prose prose-invert prose-slate max-w-none prose-p:leading-relaxed">
              <ReactMarkdown
                components={{
                  code({ node, inline, className, children, ...props }: any) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <div className="relative rounded-lg overflow-hidden border border-slate-800 my-4 shadow-xl">
                        <div className="flex items-center justify-between px-4 py-2 bg-slate-950/80 border-b border-slate-800">
                          <span className="text-xs font-mono text-slate-400 uppercase tracking-wider">{match[1]}</span>
                        </div>
                        <SyntaxHighlighter
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, background: '#020617', padding: '1rem', fontSize: '0.875rem' }}
                          {...props}
                        >
                          {String(children).replace(/\n$/, '')}
                        </SyntaxHighlighter>
                      </div>
                    ) : (
                      <code className="bg-slate-800/60 text-blue-200 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                        {children}
                      </code>
                    );
                  }
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Model badge + timestamp */}
        {!message.isLoading && (
          <div className="flex items-center gap-3 px-2 text-xs text-slate-500 font-medium">
            <span>{formatTime(message.timestamp)}</span>
            {message.model_used && (
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 font-mono text-[10px] uppercase tracking-wider text-emerald-400/80">
                {message.model_used}
              </span>
            )}
            {message.tool_calls && message.tool_calls.length > 0 && (
              <span className="text-[10px] text-slate-600">
                {message.tool_calls.length} tool{message.tool_calls.length !== 1 ? 's' : ''} used
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
