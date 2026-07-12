import React from 'react';

export const Badge = React.forwardRef(({ className = '', variant = 'default', children, ...props }, ref) => {
  return (
    <div
      ref={ref}
      className={`cm-badge cm-badge-${variant} ${className}`}
      {...props}
    >
      {children}
    </div>
  );
});

Badge.displayName = 'Badge';
