import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Brain, Trash, ArrowsClockwise } from '@phosphor-icons/react';
import { getAgentMemory, clearAgentMemory } from './api';

interface MemoryPanelProps {
  refreshTrigger: number;
}

export default function MemoryPanel({ refreshTrigger }: MemoryPanelProps) {
  const [memory, setMemory] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(false);

  const loadMemory = async () => {
    setIsLoading(true);
    try {
      const data = await getAgentMemory();
      setMemory(data.memory || {});
    } catch (err) {
      console.error('Failed to load agent memory:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadMemory();
  }, [refreshTrigger]);

  const handleClear = async () => {
    try {
      await clearAgentMemory();
      setMemory({});
    } catch (err) {
      console.error('Failed to clear agent memory:', err);
    }
  };

  const entries = Object.entries(memory);

  return (
    <div className="flex flex-col h-full" id="memory-panel">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800/60">
        <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
          <Brain size={16} weight="fill" className="text-purple-400" />
          Agent Memory
        </h3>
        <div className="flex items-center gap-1">
          <button
            onClick={loadMemory}
            disabled={isLoading}
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-colors"
            title="Refresh memory"
          >
            <ArrowsClockwise size={14} className={isLoading ? 'animate-spin' : ''} />
          </button>
          {entries.length > 0 && (
            <button
              onClick={handleClear}
              className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
              title="Clear memory"
            >
              <Trash size={14} />
            </button>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        {entries.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Brain size={32} className="text-slate-700 mb-3" />
            <p className="text-xs text-slate-600 leading-relaxed">
              No memories stored yet.
              <br />
              Ask the agent to remember something!
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {entries.map(([key, value], idx) => (
              <motion.div
                key={key}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="p-2.5 rounded-lg bg-slate-900/50 border border-slate-800/60"
              >
                <div className="text-[10px] font-semibold uppercase tracking-wider text-purple-400/80 mb-1">
                  {key}
                </div>
                <div className="text-xs text-slate-300 leading-relaxed">
                  {value}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {entries.length > 0 && (
        <div className="px-4 py-2 border-t border-slate-800/60">
          <p className="text-[10px] text-slate-600">
            {entries.length} {entries.length === 1 ? 'fact' : 'facts'} stored
          </p>
        </div>
      )}
    </div>
  );
}
