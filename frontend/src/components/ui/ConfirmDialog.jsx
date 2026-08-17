import { AlertTriangle, Info } from 'lucide-react';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogClose } from './Dialog';
import { Button } from './Button';

export function ConfirmDialog({
  open,
  onOpenChange,
  title = 'Are you sure?',
  description,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'destructive', // 'destructive' | 'primary' | 'warning'
  isLoading = false,
  onConfirm,
}) {
  if (!open) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {variant === 'destructive' ? (
            <AlertTriangle className="cm-icon-md text-red-500 flex-shrink-0" />
          ) : (
            <Info className="cm-icon-md text-blue-400 flex-shrink-0" />
          )}
          <DialogTitle>{title}</DialogTitle>
        </div>
        <DialogClose onClick={() => onOpenChange(false)} disabled={isLoading} />
      </DialogHeader>

      {description && (
        <div style={{ padding: 'var(--space-2) var(--space-4)', color: 'var(--cm-muted)', fontSize: 'var(--text-sm)' }}>
          <DialogDescription>{description}</DialogDescription>
        </div>
      )}

      <div style={{
        padding: 'var(--space-4)',
        display: 'flex',
        justifyContent: 'flex-end',
        gap: 'var(--space-2)',
        borderTop: '1px solid var(--cm-border)',
        marginTop: 'var(--space-3)',
      }}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onOpenChange(false)}
          disabled={isLoading}
        >
          {cancelLabel}
        </Button>
        <Button
          variant={variant === 'destructive' ? 'destructive' : 'default'}
          size="sm"
          onClick={onConfirm}
          isLoading={isLoading}
          disabled={isLoading}
        >
          {confirmLabel}
        </Button>
      </div>
    </Dialog>
  );
}
