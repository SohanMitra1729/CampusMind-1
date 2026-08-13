import { useEffect } from 'react';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';

export const Toast = ({ message, type = 'info', onClose, duration = 3000 }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(onClose, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const icons = {
    success: <CheckCircle className="cm-icon-md" style={{ color: 'var(--cm-success)' }} />,
    error: <AlertCircle className="cm-icon-md" style={{ color: 'var(--cm-error)' }} />,
    info: <Info className="cm-icon-md" style={{ color: 'var(--cm-info)' }} />,
  };

  return (
    <div className="cm-toast">
      {icons[type] || icons.info}
      <div className="cm-toast-msg">{message}</div>
      <button onClick={onClose} className="cm-toast-close">
        <X className="cm-icon-sm" />
      </button>
    </div>
  );
};
