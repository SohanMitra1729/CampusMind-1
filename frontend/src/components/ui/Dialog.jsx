import React from 'react';
import { X } from 'lucide-react';

export const Dialog = ({ open, onOpenChange, children }) => {
  if (!open) return null;
  return (
    <>
      <div className="cm-dialog-overlay" onClick={() => onOpenChange(false)} />
      <div className="cm-dialog-content">
        {children}
      </div>
    </>
  );
};

export const DialogHeader = ({ className = '', children, ...props }) => (
  <div className={`cm-dialog-header ${className}`} {...props}>
    {children}
  </div>
);

export const DialogTitle = ({ className = '', children, ...props }) => (
  <h2 className={`cm-dialog-title ${className}`} {...props}>
    {children}
  </h2>
);

export const DialogDescription = ({ className = '', children, ...props }) => (
  <p className={`cm-dialog-description ${className}`} {...props}>
    {children}
  </p>
);

export const DialogClose = ({ onClick, className = '', ...props }) => (
  <button 
    onClick={onClick}
    className={`cm-dialog-close ${className}`}
    {...props}
  >
    <X className="cm-icon-sm" />
    <span style={{ display: 'none' }}>Close</span>
  </button>
);
