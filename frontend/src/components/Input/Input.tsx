import { useRef, useEffect, type ChangeEvent, type KeyboardEvent } from 'react';

interface InputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit?: () => void;
  placeholder?: string;
  disabled?: boolean;
  rows?: number;
  id?: string;
  className?: string;
  innerClassName?: string;
}

export default function Input({
  value,
  onChange,
  onSubmit,
  placeholder = '',
  disabled = false,
  rows = 1,
  id,
  className = '',
  innerClassName = '',
}: InputProps) {
  const ref = useRef<HTMLTextAreaElement>(null);

  /* Auto-resize */
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  const handleChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    onChange(e.target.value);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSubmit?.();
    }
  };

  return (
    <div className={`relative flex p-1.5 rounded-[2rem] bg-slate-900/40 border border-slate-800 transition-colors focus-within:border-slate-600 focus-within:bg-slate-800/60 ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <textarea
        ref={ref}
        id={id}
        className={`w-full bg-slate-950/80 text-slate-50 placeholder:text-slate-500 rounded-[calc(2rem-0.375rem)] px-6 py-4 outline-none resize-none shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] text-base leading-relaxed ${disabled ? 'cursor-not-allowed' : ''} ${innerClassName}`}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={rows}
        style={{ minHeight: '60px', maxHeight: rows === 1 ? '160px' : 'none' }}
      />
    </div>
  );
}
