import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ChatMessage as ChatMessageType } from './types';

interface ChatMessageProps {
  message: ChatMessageType;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === 'user';
  const generatingClass = message.isGenerating ? 'opacity-80' : '';

  return (
    <article
      className={`flex gap-4 animate-[fade-in-up_0.6s_cubic-bezier(0.32,0.72,0,1)_forwards] ${isUser ? 'flex-row-reverse' : ''} ${generatingClass}`}
      id={`message-${message.id}`}
    >
      <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium mt-1 ${isUser ? 'bg-slate-800 text-slate-300' : 'bg-blue-500/10 text-blue-400'}`} aria-hidden="true">
        {isUser ? 'U' : '✦'}
      </div>

      <div className={`flex flex-col gap-1.5 max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`px-5 py-4 rounded-[1.5rem] text-base leading-relaxed overflow-hidden ${
          isUser 
            ? 'bg-indigo-900/30 border border-indigo-500/20 text-indigo-50 rounded-tr-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]' 
            : 'bg-slate-900/50 border border-slate-800 text-slate-100 rounded-tl-sm shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]'
        }`}>
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

        <div className={`flex items-center gap-3 px-2 text-xs text-slate-500 font-medium ${isUser ? 'flex-row-reverse' : ''}`}>
          <span>{formatTime(message.timestamp)}</span>
          {!isUser && message.model && (
            <span className="px-1.5 py-0.5 rounded bg-slate-800/50 border border-slate-700/50 font-mono text-[10px] uppercase tracking-wider">{message.model}</span>
          )}
        </div>
      </div>
    </article>
  );
}
