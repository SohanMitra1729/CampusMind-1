import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';

export const Button = forwardRef(({ 
  className = '', 
  variant = 'primary', 
  size = 'md', 
  isLoading = false, 
  disabled,
  children, 
  ...props 
}, ref) => {
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
