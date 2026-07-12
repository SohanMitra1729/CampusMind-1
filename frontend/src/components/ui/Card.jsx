import React from 'react';

export const Card = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`cm-card ${className}`} {...props}>
    {children}
  </div>
));
Card.displayName = 'Card';

export const CardHeader = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`cm-card-header ${className}`} {...props}>
    {children}
  </div>
));
CardHeader.displayName = 'CardHeader';

export const CardTitle = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <h3 ref={ref} className={`cm-card-title ${className}`} {...props}>
    {children}
  </h3>
));
CardTitle.displayName = 'CardTitle';

export const CardDescription = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <p ref={ref} className={`cm-card-description ${className}`} {...props}>
    {children}
  </p>
));
CardDescription.displayName = 'CardDescription';

export const CardContent = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`cm-card-content ${className}`} {...props}>
    {children}
  </div>
));
CardContent.displayName = 'CardContent';

export const CardFooter = React.forwardRef(({ className = '', children, ...props }, ref) => (
  <div ref={ref} className={`cm-card-footer ${className}`} {...props}>
    {children}
  </div>
));
CardFooter.displayName = 'CardFooter';
