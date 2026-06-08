import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import type { ModelInfo } from './api';
import ModelSelector from './ModelSelector';
import { PaperPlaneRight } from '@phosphor-icons/react';

interface ChatInputProps {
  onSend: (message: string, modelId?: string) => void;
  disabled?: boolean;
  models: ModelInfo[];
  selectedModelId: string;
  onModelChange: (modelId: string) => void;
}

export default function ChatInput({
  onSend,
  disabled = false,
  models,
  selectedModelId,
  onModelChange,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, selectedModelId);
    setValue('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col gap-3 max-w-4xl mx-auto w-full">
      <div className={`relative flex items-center p-1.5 rounded-[2rem] bg-slate-900/60 border border-slate-800 transition-colors focus-within:border-slate-700 focus-within:bg-slate-900/80 shadow-lg backdrop-blur-sm ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}>
        <textarea
          ref={textareaRef}
          className="w-full bg-transparent text-slate-50 placeholder:text-slate-500 rounded-[calc(2rem-0.375rem)] px-5 py-3.5 pr-14 outline-none resize-none text-sm leading-relaxed max-h-[200px]"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a research question..."
          disabled={disabled}
          rows={1}
          style={{ minHeight: '44px' }}
        />
        <div className="absolute right-3 bottom-3">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={disabled || !value.trim()}
            aria-label="Send message"
            className={`w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300 ${
              value.trim() && !disabled
                ? 'bg-blue-500 text-white shadow-[0_0_15px_rgba(59,130,246,0.4)] hover:bg-blue-400 hover:shadow-[0_0_20px_rgba(59,130,246,0.6)] active:scale-95'
                : 'bg-slate-800 text-slate-500 cursor-not-allowed'
            }`}
          >
            <PaperPlaneRight weight="fill" size={18} />
          </button>
        </div>
      </div>
      <div className="flex items-center justify-between px-2">
        <ModelSelector
          models={models}
          selectedModelId={selectedModelId}
          onSelect={onModelChange}
          disabled={disabled}
        />
        <div className="flex items-center gap-4 text-xs text-slate-500 font-medium tracking-wide">
          <span><kbd className="px-1.5 py-0.5 rounded-md bg-slate-800 border border-slate-700 font-mono">Enter</kbd> to send</span>
          <span>{value.length} chars</span>
        </div>
      </div>
    </div>
  );
}
