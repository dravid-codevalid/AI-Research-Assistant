import type { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  innerClassName?: string;
  hoverable?: boolean;
}

export default function Card({ children, className = '', innerClassName = '', hoverable = false }: CardProps) {
  return (
    <section 
      className={`p-1.5 rounded-[2rem] bg-slate-900/40 border border-slate-800 transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] ${hoverable ? 'hover:-translate-y-1 hover:shadow-2xl hover:shadow-blue-900/20 hover:border-slate-700' : ''} ${className}`}
    >
      <div className={`h-full w-full rounded-[calc(2rem-0.375rem)] bg-slate-950/80 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] overflow-hidden ${innerClassName}`}>
        {children}
      </div>
    </section>
  );
}
