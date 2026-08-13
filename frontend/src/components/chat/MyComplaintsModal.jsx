/**
 * src/components/chat/MyComplaintsModal.jsx — Student Complaints History Modal
 */

import { Loader2 } from 'lucide-react';
import { Dialog, DialogHeader, DialogTitle, DialogClose } from '../ui/Dialog';
import { Badge } from '../ui/Badge';

export default function MyComplaintsModal({
  showMyComplaints,
  setShowMyComplaints,
  myComplaints,
  myComplaintsLoading,
}) {
  if (!showMyComplaints) return null;

  return (
    <Dialog open={showMyComplaints} onOpenChange={setShowMyComplaints}>
      <DialogHeader>
        <DialogTitle>📋 My Filed Complaints</DialogTitle>
        <DialogClose onClick={() => setShowMyComplaints(false)} />
      </DialogHeader>

      <div style={{ maxHeight: '400px', overflowY: 'auto', padding: 'var(--space-2)' }}>
        {myComplaintsLoading ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
            <Loader2 className="animate-spin cm-icon-md mx-auto mb-2" /> Loading complaints...
          </div>
        ) : myComplaints.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
            You haven't submitted any complaints yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-3)' }}>
            {myComplaints.map((c) => (
              <div
                key={c.id}
                style={{
                  padding: 'var(--space-3)',
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--cm-bg)',
                  border: '1px solid var(--cm-border)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-1)' }}>
                  <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)', color: 'var(--cm-fg)' }}>
                    {c.category_icon} {c.title}
                  </span>
                  <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                    {c.status_icon} {c.status_label}
                  </Badge>
                </div>
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', marginBottom: 'var(--space-2)' }}>
                  {c.description}
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--cm-muted)' }}>
                  <span>Category: {c.category}</span>
                  <span>Votes: {c.vote_count}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Dialog>
  );
}
