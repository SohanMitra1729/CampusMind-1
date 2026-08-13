import { useState, useRef, useEffect } from 'react';

export const Dropdown = ({ trigger, children, className = '' }) => {
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <div onClick={() => setOpen(!open)} style={{cursor: 'pointer'}}>
        {trigger}
      </div>
      {open && (
        <div className={`absolute right-0 mt-2 cm-dropdown-content ${className}`}>
          {children}
        </div>
      )}
    </div>
  );
};

export const DropdownItem = ({ children, onClick, className = '', ...props }) => (
  <div
    className={`cm-dropdown-item ${className}`}
    onClick={onClick}
    {...props}
  >
    {children}
  </div>
);
