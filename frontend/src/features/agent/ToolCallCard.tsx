import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CaretDown, Globe, FloppyDisk, Brain } from '@phosphor-icons/react';
import type { ToolCall } from './types';

interface ToolCallCardProps {
  toolCall: ToolCall;
  index: number;
}

const TOOL_ICONS: Record<string, React.ReactNode> = {
  web_search: <Globe size={16} weight="bold" />,
  remember_fact: <FloppyDisk size={16} weight="bold" />,
  recall_fact: <Brain size={16} weight="bold" />,
};

const TOOL_LABELS: Record<string, string> = {
  web_search: 'Web Search',
  remember_fact: 'Store Memory',
  recall_fact: 'Recall Memory',
};

const TOOL_COLORS: Record<string, string> = {
  web_search: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  remember_fact: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  recall_fact: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
};

function formatInput(input: string): string {
  try {
    const parsed = JSON.parse(input);
    if (typeof parsed === 'object') {
      return Object.entries(parsed)
        .map(([k, v]) => `${k}: ${v}`)
        .join(', ');
    }
    return input;
  } catch {
    return input;
  }
}

export default function ToolCallCard({ toolCall, index }: ToolCallCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const icon = TOOL_ICONS[toolCall.tool] || <Brain size={16} weight="bold" />;
  const label = TOOL_LABELS[toolCall.tool] || toolCall.tool;
  const colorClass = TOOL_COLORS[toolCall.tool] || 'text-slate-400 bg-slate-500/10 border-slate-500/20';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.3 }}
      className={`rounded-xl border overflow-hidden ${colorClass}`}
    >
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2.5 px-3.5 py-2.5 text-left text-sm font-medium transition-colors hover:bg-white/[0.03]"
        id={`tool-call-${index}`}
      >
        <span className="flex-shrink-0 opacity-80">{icon}</span>
        <span className="flex-1 truncate">{label}</span>
        <span className="text-xs opacity-50 truncate max-w-[200px] font-normal">
          {formatInput(toolCall.input)}
        </span>
        <motion.span
          animate={{ rotate: isExpanded ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="flex-shrink-0 opacity-50"
        >
          <CaretDown size={14} />
        </motion.span>
      </button>

      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="border-t border-inherit"
          >
            <div className="px-3.5 py-3 space-y-2.5 text-xs">
              <div>
                <span className="font-semibold opacity-60 uppercase tracking-wider text-[10px]">
                  Input
                </span>
                <pre className="mt-1 p-2 rounded-lg bg-black/20 text-slate-300 whitespace-pre-wrap break-words font-mono">
                  {formatInput(toolCall.input)}
                </pre>
              </div>
              <div>
                <span className="font-semibold opacity-60 uppercase tracking-wider text-[10px]">
                  Output
                </span>
                <pre className="mt-1 p-2 rounded-lg bg-black/20 text-slate-300 whitespace-pre-wrap break-words font-mono leading-relaxed max-h-48 overflow-y-auto">
                  {toolCall.output}
                </pre>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
