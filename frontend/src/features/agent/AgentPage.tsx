import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { PaperPlaneTilt, Trash, Robot } from '@phosphor-icons/react';
import { useAgent } from './hooks/useAgent';
import { useWorkspace } from '../../context/WorkspaceContext';
import AgentMessage from './AgentMessage';
import MemoryPanel from './MemoryPanel';
import { getAgentModelInfo, type ModelInfo } from './api';

export default function AgentPage() {
  const { messages, isLoading, error, sendMessage, clearChat } = useAgent();
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);

  // Fetch model info on mount
  useEffect(() => {
    getAgentModelInfo()
      .then((data) => setModelInfo(data))
      .catch((err) => console.error('Failed to fetch agent model info:', err));
  }, []);

  const { activeUser, activeWorkspace } = useWorkspace();
  const [input, setInput] = useState('');
  const [memoryRefresh, setMemoryRefresh] = useState(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Refresh memory panel after agent responds
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      setMemoryRefresh((prev) => prev + 1);
    }
  }, [isLoading, messages.length]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    sendMessage(trimmed, activeUser?.id, activeWorkspace?.id);
    setInput('');

    // Reset textarea height
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 160) + 'px';
  };

  return (
    <div className="flex h-full w-full" id="agent-page">
      {/* ── Main Agent Chat Area ── */}
      <div className="flex-1 flex flex-col min-h-0 min-w-0">
        {/* Header */}
        <header className="shrink-0 h-12 flex items-center justify-between px-6 border-b border-slate-800/40 bg-slate-950/60 backdrop-blur-sm">
          <h2 className="text-sm font-medium text-slate-300 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <Robot size={16} weight="fill" className="text-emerald-400" />
            AI Agent
            <span className="text-xs text-slate-600 font-normal ml-1">
              Web Search · File Memory
            </span>
            {modelInfo && (
              <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold ml-3 border ${
                modelInfo.source === 'mlflow'
                  ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                  : 'bg-slate-800/80 text-slate-400 border-slate-700/50'
              }`}>
                {modelInfo.source === 'mlflow' ? (
                  <>
                    <span className="w-1 h-1 rounded-full bg-indigo-400 animate-pulse" />
                    Registry: {modelInfo.model_name} v{modelInfo.version}
                    {modelInfo.val_score !== null && ` (F1: ${modelInfo.val_score.toFixed(0)}%)`}
                  </>
                ) : (
                  <>
                    Fallback: {modelInfo.model_name}
                  </>
                )}
              </span>
            )}
          </h2>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-400 transition-colors"
            >
              <Trash size={14} />
              Clear
            </button>
          )}
        </header>

        {/* Messages area */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="max-w-3xl mx-auto px-6 py-6 space-y-6">
            {messages.length === 0 && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6 }}
                className="flex flex-col items-center justify-center py-20 text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-5">
                  <Robot size={32} weight="fill" className="text-emerald-400" />
                </div>
                <h2 className="text-xl font-semibold text-slate-200 mb-2">
                  AI Research Agent
                </h2>
                <p className="text-sm text-slate-500 max-w-md leading-relaxed">
                  I can search the web for factual information and remember things
                  across conversations. Try asking me a research question!
                </p>
                <div className="flex flex-wrap justify-center gap-2 mt-6">
                  {[
                    'Who invented Python?',
                    'Remember that pi ≈ 3.14159',
                    'What do you know about France?',
                  ].map((q) => (
                    <button
                      key={q}
                      onClick={() => {
                        setInput(q);
                        textareaRef.current?.focus();
                      }}
                      className="px-3 py-1.5 rounded-full text-xs text-slate-400 bg-slate-900/50 border border-slate-800 hover:border-emerald-500/30 hover:text-emerald-400 transition-colors"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </motion.div>
            )}

            {messages.map((msg) => (
              <AgentMessage key={msg.id} message={msg} />
            ))}

            {error && (
              <div className="px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/20 text-sm text-red-400">
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input bar */}
        <div className="shrink-0 border-t border-slate-800/40 bg-slate-950/80 backdrop-blur-sm px-6 py-4">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-end gap-3 p-2 rounded-2xl bg-slate-900/50 border border-slate-800 focus-within:border-emerald-500/30 transition-colors">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={handleTextareaInput}
                onKeyDown={handleKeyDown}
                placeholder="Ask the agent a question... (Enter to send)"
                rows={1}
                disabled={isLoading}
                className="flex-1 bg-transparent text-slate-100 text-sm placeholder:text-slate-600 resize-none focus:outline-none px-3 py-2 max-h-40"
                id="agent-input"
              />
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                id="agent-send-btn"
              >
                <PaperPlaneTilt size={18} weight="fill" />
              </button>
            </div>
            <p className="text-[10px] text-slate-700 mt-2 text-center">
              Agent uses web search and file memory tools · Powered by DSPy ReAct
            </p>
          </div>
        </div>
      </div>

      {/* ── Memory Sidebar ── */}
      <aside className="w-64 shrink-0 hidden lg:flex lg:flex-col border-l border-slate-800/60 bg-slate-950/80">
        <MemoryPanel refreshTrigger={memoryRefresh} />
      </aside>
    </div>
  );
}
