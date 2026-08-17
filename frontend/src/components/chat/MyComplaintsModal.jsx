/**
 * src/components/chat/MyComplaintsModal.jsx — Student Complaints History Modal
 * Shows complaint status, category, assigned staff role, scope, and vote count.
 */

import { Loader2 } from 'lucide-react';
import { Dialog, DialogHeader, DialogTitle, DialogClose } from '../ui/Dialog';
import { Badge } from '../ui/Badge';

// Staff role metadata for student-facing display
const STAFF_ROLE_META = {
  electrical:   { label: 'Electrical / Maintenance',           icon: '⚡' },
  cleaning:     { label: 'Cleaning Staff',                     icon: '🧹' },
  maintenance:  { label: 'Maintenance (Furniture / Plumbing)', icon: '🛠️' },
  mess_manager: { label: 'Mess Manager',                       icon: '🍽️' },
  watchmen:     { label: 'Watchmen / Security',                icon: '🔒' },
};

const SCOPE_META = {
  MESS:            { label: 'Mess / Dining',       icon: '🍽️' },
  ROOM_SHARED:     { label: 'Room Shared',         icon: '👥' },
  ROOM_INDIVIDUAL: { label: 'Personal Item',       icon: '👤' },
  COMMON_AREA:     { label: 'Common Area',         icon: '🏢' },
};

function StaffRoleChip({ role }) {
  const meta = STAFF_ROLE_META[role];
  const text = meta ? `${meta.icon} Assigned: ${meta.label}` : null;
  if (!text) return null;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '10px',
      fontWeight: 600,
      padding: '2px 8px',
      borderRadius: '999px',
      background: 'rgba(99,102,241,0.1)',
      color: '#a5b4fc',
      border: '1px solid rgba(99,102,241,0.25)',
    }}>
      {text}
    </span>
  );
}

function ScopeChip({ scope }) {
  const meta = SCOPE_META[scope];
  if (!meta) return null;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '4px',
      fontSize: '10px',
      fontWeight: 600,
      padding: '2px 8px',
      borderRadius: '999px',
      background: 'rgba(148,163,184,0.1)',
      color: '#94a3b8',
      border: '1px solid rgba(148,163,184,0.25)',
    }}>
      {meta.icon} {meta.label}
    </span>
  );
}

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

      <div style={{ maxHeight: '420px', overflowY: 'auto', padding: 'var(--space-2)' }}>
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
                {/* Title + Status */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-1)', gap: '8px' }}>
                  <span style={{ fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)', color: 'var(--cm-fg)' }}>
                    {c.category_icon} {c.title}
                  </span>
                  <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                    {c.status_icon} {c.status_label}
                  </Badge>
                </div>

                {/* Staff role & Scope chips */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '6px' }}>
                  {c.staff_role && <StaffRoleChip role={c.staff_role} />}
                  {c.scope && <ScopeChip scope={c.scope} />}
                </div>

                {/* Description */}
                <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', marginBottom: 'var(--space-2)', lineHeight: 1.5 }}>
                  {c.description}
                </p>

                {/* Footer meta */}
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--cm-muted)' }}>
                  <span>Category: {c.category}</span>
                  <span>👥 {c.vote_count} {c.vote_count === 1 ? 'vote' : 'votes'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Dialog>
  );
}
