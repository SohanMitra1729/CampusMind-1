import React from 'react';
import { Loader2 } from 'lucide-react';

export const Button = React.forwardRef(({ 
  className = '', 
  variant = 'primary', 
  size = 'md', 
  isLoading = false, 
  disabled,
  children, 
  ...props 
}, ref) => {
  const baseStyles = 'inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none ring-offset-background';
  
  const variants = {
    primary: 'bg-[var(--cm-primary)] text-[var(--cm-primary-fg)] hover:bg-[var(--cm-primary)]/90',
    secondary: 'bg-[var(--cm-secondary)] text-[var(--cm-secondary-fg)] hover:bg-[var(--cm-secondary)]/80',
    outline: 'border border-[var(--cm-border)] hover:bg-[var(--cm-secondary)] text-[var(--cm-fg)]',
    ghost: 'hover:bg-[var(--cm-secondary)] text-[var(--cm-fg)]',
    danger: 'bg-[var(--cm-error)] text-white hover:bg-[var(--cm-error)]/90',
  };

  const sizes = {
    sm: 'h-9 px-3 text-xs',
    md: 'h-10 py-2 px-4 text-sm',
    lg: 'h-11 px-8 text-base',
    icon: 'h-10 w-10',
  };

  // Note: Since we are migrating from plain CSS, we map these utility classes to inline styles or rely on the global CSS.
  // Actually, to ensure it works without Tailwind, I should write plain CSS or inline styles for these, or add the classes to index.css.
  // The instructions said "Do NOT rewrite global CSS entirely, preserve existing globals".
  // Let's use standard CSS modules or a clean class structure.
  
  return (
    <button
      ref={ref}
      disabled={isLoading || disabled}
      className={`cm-btn cm-btn-${variant} cm-btn-${size} ${className}`}
      {...props}
    >
      {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
      {children}
    </button>
  );
});

Button.displayName = 'Button';
