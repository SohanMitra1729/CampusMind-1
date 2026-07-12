import React from 'react';
import { Loader2 } from 'lucide-react';

export const Loader = ({ className = '', size = 24, ...props }) => {
  return (
    <Loader2 
      className={`animate-spin text-[var(--cm-muted)] ${className}`} 
      size={size} 
      {...props} 
    />
  );
};
