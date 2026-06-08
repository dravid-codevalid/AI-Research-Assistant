import type { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  icon?: ReactNode;
}

export default function Button({
  children,
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  disabled,
  className = '',
  ...rest
}: ButtonProps) {
  const baseClasses = "group relative inline-flex items-center justify-center font-medium rounded-full transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] active:scale-[0.98] outline-none focus-visible:ring-2 focus-visible:ring-blue-500/50";
  
  const variants = {
    primary: "bg-slate-50 text-slate-950 hover:bg-white shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.2)]",
    secondary: "bg-slate-900/50 text-slate-50 border border-slate-700 hover:bg-slate-800 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]",
    ghost: "bg-transparent text-slate-300 hover:text-white hover:bg-white/5",
  };
  
  const sizes = {
    sm: "px-4 py-2 text-sm",
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  };

  const isDisabled = disabled || loading;

  return (
    <button
      className={`${baseClasses} ${variants[variant]} ${sizes[size]} ${isDisabled ? 'opacity-50 cursor-not-allowed active:scale-100' : ''} ${className}`}
      disabled={isDisabled}
      {...rest}
    >
      {loading && (
        <span className="mr-2 animate-spin border-2 border-current border-t-transparent rounded-full w-4 h-4" aria-hidden="true" />
      )}
      <span className="relative z-10 whitespace-nowrap">{children}</span>
      {icon && (
        <span className={`ml-3 flex items-center justify-center rounded-full transition-transform duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1 group-hover:-translate-y-[1px] group-hover:scale-105 ${
          variant === 'primary' ? 'bg-slate-950/10' : 'bg-white/10'
        } ${size === 'sm' ? 'w-6 h-6' : size === 'lg' ? 'w-10 h-10' : 'w-8 h-8'}`}>
          {icon}
        </span>
      )}
    </button>
  );
}
