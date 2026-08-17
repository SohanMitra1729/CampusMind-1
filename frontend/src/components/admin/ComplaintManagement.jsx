/**
 * src/components/admin/ComplaintManagement.jsx — Complaints Admin Table & Status Action Buttons
 *
 * Shows assigned staff role badge, scope badge, filters for status/category/role/scope,
 * and allows admins to update complaint statuses.
 */

import { AlertCircle, RefreshCw, Users, User as UserIcon, Home, DoorOpen } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

// Staff role display metadata
const STAFF_ROLE_META = {
  electrical:   { label: 'Electrical / Maintenance',               icon: '⚡',   badgeStyle: { background: 'rgba(234,179,8,0.15)',  color: '#facc15', border: '1px solid rgba(234,179,8,0.3)'  } },
  cleaning:     { label: 'Cleaning Staff',                         icon: '🧹',  badgeStyle: { background: 'rgba(34,197,94,0.12)', color: '#4ade80', border: '1px solid rgba(34,197,94,0.3)' } },
  maintenance:  { label: 'Maintenance (Furniture / Plumbing)',     icon: '🛠️',  badgeStyle: { background: 'rgba(14,165,233,0.12)', color: '#38bdf8', border: '1px solid rgba(14,165,233,0.3)' } },
  mess_manager: { label: 'Mess Manager',                          icon: '🍽️', badgeStyle: { background: 'rgba(249,115,22,0.12)', color: '#fb923c', border: '1px solid rgba(249,115,22,0.3)' } },
  watchmen:     { label: 'Watchmen / Security',                   icon: '🔒',  badgeStyle: { background: 'rgba(99,102,241,0.12)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)' } },
};

// Scope display metadata
const SCOPE_META = {
  MESS:            { label: 'Mess / Dining',        icon: '🍽️', badgeStyle: { background: 'rgba(236,72,153,0.12)', color: '#f472b6', border: '1px solid rgba(236,72,153,0.3)' } },
  ROOM_SHARED:     { label: 'Room Shared Fixture',  icon: '👥', badgeStyle: { background: 'rgba(168,85,247,0.12)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)' } },
  ROOM_INDIVIDUAL: { label: 'Personal Item',        icon: '👤', badgeStyle: { background: 'rgba(59,130,246,0.12)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)' } },
  COMMON_AREA:     { label: 'Common Area',          icon: '🏢', badgeStyle: { background: 'rgba(100,116,139,0.12)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.3)' } },
};

const UNASSIGNED_STYLE = {
  background: 'rgba(100,116,139,0.12)',
  color: '#94a3b8',
  border: '1px solid rgba(100,116,139,0.3)',
};

function StaffRoleBadge({ role }) {
  const meta = STAFF_ROLE_META[role];
  if (!meta) {
    return (
      <span style={{
        ...UNASSIGNED_STYLE,
        fontSize: '10px', padding: '2px 8px', borderRadius: '999px',
        fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px',
      }}>
        🏛️ Unassigned / Academic
      </span>
    );
  }
  return (
    <span style={{
      ...meta.badgeStyle,
      fontSize: '10px', padding: '2px 8px', borderRadius: '999px',
      fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px',
    }}>
      {meta.icon} {meta.label}
    </span>
  );
}

function ScopeBadge({ scope }) {
  const meta = SCOPE_META[scope] || SCOPE_META.COMMON_AREA;
  return (
    <span style={{
      ...meta.badgeStyle,
      fontSize: '10px', padding: '2px 8px', borderRadius: '999px',
      fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px',
    }}>
      {meta.icon} {meta.label}
    </span>
  );
}

export default function ComplaintManagement({
  complaints,
  isLoadingComplaints,
  complaintStatusFilter,
  setComplaintStatusFilter,
  complaintCategoryFilter,
  setComplaintCategoryFilter,
  complaintStaffRoleFilter,
  setComplaintStaffRoleFilter,
  complaintScopeFilter,
  setComplaintScopeFilter,
  fetchComplaints,
  updateComplaintStatus,
  updatingComplaintId,
  formatDate,
}) {
  const selectStyle = {
    padding: 'var(--space-2)',
    borderRadius: 'var(--radius-md)',
    background: 'var(--cm-bg)',
    color: 'var(--cm-fg)',
    border: '1px solid var(--cm-border)',
    fontSize: 'var(--text-xs)',
  };

  return (
    <div className="admin-tab-content">
      <Card>
        <CardHeader style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
          <div>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <AlertCircle className="cm-icon-md text-[var(--cm-accent)]" /> Student Complaints ({complaints.length})
            </CardTitle>
            <CardDescription>View, route, and update ticket statuses across campus departments.</CardDescription>
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* Status filter */}
            <select
              style={selectStyle}
              value={complaintStatusFilter}
              onChange={(e) => {
                setComplaintStatusFilter(e.target.value);
                fetchComplaints(e.target.value, complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
              }}
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>

            {/* Category filter */}
            <select
              style={selectStyle}
              value={complaintCategoryFilter}
              onChange={(e) => {
                setComplaintCategoryFilter(e.target.value);
                fetchComplaints(complaintStatusFilter, e.target.value, complaintStaffRoleFilter, complaintScopeFilter);
              }}
            >
              <option value="">All Categories</option>
              <option value="hostel">Hostel</option>
              <option value="academic">Academic</option>
              <option value="facility">Facility</option>
              <option value="mess">Mess</option>
              <option value="transport">Transport</option>
              <option value="admin">Admin</option>
              <option value="general">General</option>
            </select>

            {/* Staff role filter */}
            <select
              style={selectStyle}
              value={complaintStaffRoleFilter}
              onChange={(e) => {
                setComplaintStaffRoleFilter(e.target.value);
                fetchComplaints(complaintStatusFilter, complaintCategoryFilter, e.target.value, complaintScopeFilter);
              }}
            >
              <option value="">All Staff Roles</option>
              <option value="electrical">⚡ Electrical</option>
              <option value="cleaning">🧹 Cleaning</option>
              <option value="maintenance">🛠️ Maintenance</option>
              <option value="mess_manager">🍽️ Mess Manager</option>
              <option value="watchmen">🔒 Watchmen</option>
            </select>

            {/* Scope filter */}
            <select
              style={selectStyle}
              value={complaintScopeFilter}
              onChange={(e) => {
                setComplaintScopeFilter(e.target.value);
                fetchComplaints(complaintStatusFilter, complaintCategoryFilter, complaintStaffRoleFilter, e.target.value);
              }}
            >
              <option value="">All Scopes</option>
              <option value="MESS">🍽️ Mess Scope</option>
              <option value="ROOM_SHARED">👥 Room Shared</option>
              <option value="ROOM_INDIVIDUAL">👤 Individual Item</option>
              <option value="COMMON_AREA">🏢 Common Area</option>
            </select>

            <Button variant="ghost" size="sm" onClick={() => fetchComplaints(complaintStatusFilter, complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter)}>
              <RefreshCw className="cm-icon-sm mr-1" /> Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {isLoadingComplaints ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              <RefreshCw className="animate-spin cm-icon-md mx-auto mb-2" /> Loading complaints...
            </div>
          ) : complaints.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              No complaints match the current filters.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
              {complaints.map((c) => (
                <Card key={c.id} style={{ background: 'var(--cm-bg)', border: '1px solid var(--cm-border)' }}>
                  <CardContent className="p-6">
                    {/* Header row */}
                    <div className="admin-complaint-header-row">
                      <div className="flex gap-3">
                        <div className="text-2xl mt-1">{c.category_icon}</div>
                        <div style={{ flex: 1 }}>
                          <div className="font-semibold text-lg mb-1">{c.title}</div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--cm-muted)' }}>
                            <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                              {c.status === 'open' ? 'Open' : c.status === 'in_progress' ? 'In Progress' : c.status === 'resolved' ? 'Resolved' : 'Dismissed'}
                            </Badge>

                            {/* Staff role badge */}
                            <StaffRoleBadge role={c.staff_role} />

                            {/* Scope badge */}
                            <ScopeBadge scope={c.scope} />

                            <span className="flex items-center gap-1"><UserIcon className="cm-icon-xs" /> {c.student_name} ({c.scholar_id})</span>
                            <span className="flex items-center gap-1"><Users className="cm-icon-xs" /> {c.vote_count} votes</span>
                            <span>{formatDate(c.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Location row */}
                    {(c.hostel_id || c.room_number || c.mess_id) && (
                      <div style={{ marginTop: '12px', display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '12px', color: 'var(--cm-muted)' }}>
                        {c.hostel_id && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Home size={12} /> Hostel Linked
                          </span>
                        )}
                        {c.room_number && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <DoorOpen size={12} /> Room {c.room_number}
                          </span>
                        )}
                        {c.mess_id && (
                          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            🍽️ {c.mess_id}
                          </span>
                        )}
                      </div>
                    )}

                    {/* Description */}
                    <p className="mt-4 text-sm text-[var(--cm-fg)] leading-relaxed">
                      {c.description}
                    </p>

                    {/* Actions */}
                    <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
                      {c.status !== 'in_progress' && (
                        <Button size="xs" variant="secondary" onClick={() => updateComplaintStatus(c.id, 'in_progress')} isLoading={updatingComplaintId === c.id}>
                          Mark In Progress
                        </Button>
                      )}
                      {c.status !== 'resolved' && (
                        <Button size="xs" onClick={() => updateComplaintStatus(c.id, 'resolved')} isLoading={updatingComplaintId === c.id}>
                          Mark Resolved
                        </Button>
                      )}
                      {c.status !== 'dismissed' && (
                        <Button size="xs" variant="ghost" onClick={() => updateComplaintStatus(c.id, 'dismissed')} isLoading={updatingComplaintId === c.id} style={{ color: 'var(--cm-muted)' }}>
                          Dismiss
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
