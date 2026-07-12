import React from 'react';

export const Input = React.forwardRef(({ className = '', ...props }, ref) => {
  return (
    <input
      className={`cm-input ${className}`}
      ref={ref}
      {...props}
    />
  );
});

Input.displayName = 'Input';
