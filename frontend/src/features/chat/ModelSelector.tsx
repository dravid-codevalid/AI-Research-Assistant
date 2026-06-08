import { useState, useRef, useEffect } from 'react';
import type { ModelInfo } from './api';
import { CaretDown, Sparkle } from '@phosphor-icons/react';

interface ModelSelectorProps {
  models: ModelInfo[];
  selectedModelId: string;
  onSelect: (modelId: string) => void;
  disabled?: boolean;
}

export default function ModelSelector({
  models,
  selectedModelId,
  onSelect,
  disabled = false,
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selected = models.find((m) => m.id === selectedModelId);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative inline-block" ref={containerRef}>
      <button
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border bg-slate-900/50 backdrop-blur-sm text-xs font-medium transition-colors ${
          open ? 'border-blue-500/50 text-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.1)]' : 'border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
        } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        type="button"
      >
        <Sparkle weight="fill" className={open ? 'text-blue-500' : 'text-slate-500'} />
        <span>{selected?.display_name ?? 'Select model'}</span>
        <CaretDown className={`transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="absolute left-0 bottom-full mb-2 w-72 bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-50 animate-[fade-in-up_0.2s_ease-out_forwards] origin-bottom-left">
          <ul className="max-h-64 overflow-y-auto p-1.5 space-y-0.5">
            {models.map((model) => (
              <li
                key={model.id}
                className={`px-3 py-2.5 rounded-xl cursor-pointer transition-colors ${
                  model.id === selectedModelId
                    ? 'bg-blue-500/10 text-blue-400'
                    : 'text-slate-300 hover:bg-slate-800/80 hover:text-slate-100'
                }`}
                onClick={() => {
                  onSelect(model.id);
                  setOpen(false);
                }}
              >
                <div className="flex items-center justify-between mb-0.5">
                  <span className="font-medium text-sm">{model.display_name}</span>
                  <span className="text-[10px] uppercase tracking-widest font-bold opacity-60">
                    {model.provider}
                  </span>
                </div>
                <p className="text-xs opacity-70 line-clamp-2 leading-relaxed">
                  {model.description}
                </p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
