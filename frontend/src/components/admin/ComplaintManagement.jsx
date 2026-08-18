/**
 * src/components/admin/ComplaintManagement.jsx — Complaints Admin Dashboard & Ticket Lifecycle
 * ─────────────────────────────────────────────────────────────────────────────
 * Provides:
 *   1. Filterable status pills, category, staff role, and boundary scope selectors
 *   2. Modern ticket cards with Lucide icons, clear metadata hierarchy, and location chips
 *   3. Explicit, sensible status lifecycle transitions:
 *      - Open ➔ In Progress / Resolved / Dismissed / Delete
 *      - In Progress ➔ Resolved / Revert to Open / Dismiss / Delete
 *      - Resolved ➔ Reopen / Delete
 *      - Dismissed ➔ Reopen / Delete Permanently
 *   4. Permanent delete confirmation modal
 */

import { useState, useMemo } from 'react';
import {
  AlertCircle,
  RefreshCw,
  Users,
  User,
  Home,
  DoorOpen,
  Zap,
  Brush,
  Wrench,
  UtensilsCrossed,
  ShieldCheck,
  Building2,
  CheckCircle2,
  Clock,
  XCircle,
  RotateCcw,
  Trash2,
  ArrowRight,
  GraduationCap,
  Bus,
  Tag,
  ThumbsUp,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { ConfirmDialog } from '../ui/ConfirmDialog';

// Category metadata with Lucide icons
const CATEGORY_META = {
  hostel:    { label: 'Hostel',    icon: Home,            color: '#60a5fa', bg: 'rgba(59,130,246,0.12)' },
  academic:  { label: 'Academic',  icon: GraduationCap,   color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
  facility:  { label: 'Facility',  icon: Wrench,          color: '#38bdf8', bg: 'rgba(56,189,248,0.12)' },
  mess:      { label: 'Mess',      icon: UtensilsCrossed, color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
  transport: { label: 'Transport', icon: Bus,             color: '#f472b6', bg: 'rgba(244,114,182,0.12)' },
  admin:     { label: 'Admin',     icon: Building2,       color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' },
  general:   { label: 'General',   icon: Tag,             color: '#cbd5e1', bg: 'rgba(203,213,225,0.12)' },
};

// Staff role metadata with Lucide icons
const STAFF_ROLE_META = {
  electrical:   { label: 'Electrical',    icon: Zap,             color: '#facc15', bg: 'rgba(250,204,21,0.12)', border: 'rgba(250,204,21,0.3)' },
  cleaning:     { label: 'Cleaning Staff',icon: Brush,           color: '#4ade80', bg: 'rgba(74,222,128,0.12)', border: 'rgba(74,222,128,0.3)' },
  maintenance:  { label: 'Maintenance',   icon: Wrench,          color: '#38bdf8', bg: 'rgba(56,189,248,0.12)', border: 'rgba(56,189,248,0.3)' },
  mess_manager: { label: 'Mess Manager',  icon: UtensilsCrossed, color: '#fb923c', bg: 'rgba(251,146,60,0.12)', border: 'rgba(251,146,60,0.3)' },
  watchmen:     { label: 'Security Staff',icon: ShieldCheck,     color: '#818cf8', bg: 'rgba(129,140,248,0.12)', border: 'rgba(129,140,248,0.3)' },
};

// Scope display metadata with Lucide icons
const SCOPE_META = {
  MESS:            { label: 'Mess Dining',  icon: UtensilsCrossed, color: '#f472b6', bg: 'rgba(244,114,182,0.12)', border: 'rgba(244,114,182,0.3)' },
  ROOM_SHARED:     { label: 'Room Shared',  icon: Users,           color: '#c084fc', bg: 'rgba(192,132,252,0.12)', border: 'rgba(192,132,252,0.3)' },
  ROOM_INDIVIDUAL: { label: 'Personal Item',icon: User,            color: '#60a5fa', bg: 'rgba(96,165,250,0.12)', border: 'rgba(96,165,250,0.3)' },
  COMMON_AREA:     { label: 'Common Area',  icon: Building2,       color: '#94a3b8', bg: 'rgba(148,163,184,0.12)', border: 'rgba(148,163,184,0.3)' },
};

function StaffRoleBadge({ role }) {
  const meta = STAFF_ROLE_META[role];
  if (!meta) {
    return (
      <span className="admin-ticket-chip" style={{ background: 'rgba(100,116,139,0.12)', color: '#94a3b8', border: '1px solid rgba(100,116,139,0.25)' }}>
        <Building2 size={11} /> Unassigned / Academic
      </span>
    );
  }
  const IconComp = meta.icon;
  return (
    <span className="admin-ticket-chip" style={{ background: meta.bg, color: meta.color, border: `1px solid ${meta.border}` }}>
      <IconComp size={11} /> {meta.label}
    </span>
  );
}

function ScopeBadge({ scope }) {
  const meta = SCOPE_META[scope] || SCOPE_META.COMMON_AREA;
  const IconComp = meta.icon;
  return (
    <span className="admin-ticket-chip" style={{ background: meta.bg, color: meta.color, border: `1px solid ${meta.border}` }}>
      <IconComp size={11} /> {meta.label}
    </span>
  );
}

function StatusBadge({ status }) {
  if (status === 'open') {
    return (
      <span className="admin-status-badge status-open">
        <span className="admin-status-dot dot-open" /> Open
      </span>
    );
  }
  if (status === 'in_progress') {
    return (
      <span className="admin-status-badge status-in-progress">
        <span className="admin-status-dot dot-in-progress" /> In Progress
      </span>
    );
  }
  if (status === 'resolved') {
    return (
      <span className="admin-status-badge status-resolved">
        <CheckCircle2 size={12} /> Resolved
      </span>
    );
  }
  return (
    <span className="admin-status-badge status-dismissed">
      <XCircle size={12} /> Dismissed
    </span>
  );
}

export default function ComplaintManagement({
  complaints = [],
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
  deleteComplaint,
  deletingComplaintId,
  formatDate,
}) {
  const [complaintToDelete, setComplaintToDelete] = useState(null);

  // Status counts for quick filter buttons
  const counts = useMemo(() => {
    return {
      all: complaints.length,
      open: complaints.filter((c) => c.status === 'open').length,
      in_progress: complaints.filter((c) => c.status === 'in_progress').length,
      resolved: complaints.filter((c) => c.status === 'resolved').length,
      dismissed: complaints.filter((c) => c.status === 'dismissed').length,
    };
  }, [complaints]);

  const handleFilterChange = (statusVal, catVal, roleVal, scopeVal) => {
    fetchComplaints(statusVal, catVal, roleVal, scopeVal);
  };

  const confirmDeleteComplaint = async () => {
    if (!complaintToDelete || !deleteComplaint) return;
    await deleteComplaint(complaintToDelete.id);
    setComplaintToDelete(null);
  };

  return (
    <div className="admin-tab-content">
      {/* Permanent Delete Confirmation Dialog */}
      <ConfirmDialog
        open={Boolean(complaintToDelete)}
        onOpenChange={(open) => {
          if (!open) setComplaintToDelete(null);
        }}
        title="Permanently Delete Complaint Ticket?"
        description={`Are you sure you want to permanently delete ticket '${complaintToDelete?.title}' submitted by ${complaintToDelete?.student_name}? This action cannot be undone.`}
        confirmLabel="Delete Ticket"
        variant="destructive"
        isLoading={Boolean(deletingComplaintId)}
        onConfirm={confirmDeleteComplaint}
      />

      {/* ── Status Quick Filter Bar ── */}
      <div className="admin-complaints-status-bar">
        <button
          className={`admin-status-tab ${complaintStatusFilter === '' ? 'active' : ''}`}
          onClick={() => {
            setComplaintStatusFilter('');
            handleFilterChange('', complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
          }}
        >
          All Tickets <span className="admin-status-tab-count">{counts.all}</span>
        </button>

        <button
          className={`admin-status-tab ${complaintStatusFilter === 'open' ? 'active' : ''}`}
          onClick={() => {
            setComplaintStatusFilter('open');
            handleFilterChange('open', complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
          }}
        >
          <span className="admin-status-dot dot-open" /> Open
          {counts.open > 0 && <span className="admin-status-tab-count count-open">{counts.open}</span>}
        </button>

        <button
          className={`admin-status-tab ${complaintStatusFilter === 'in_progress' ? 'active' : ''}`}
          onClick={() => {
            setComplaintStatusFilter('in_progress');
            handleFilterChange('in_progress', complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
          }}
        >
          <span className="admin-status-dot dot-in-progress" /> In Progress
          {counts.in_progress > 0 && <span className="admin-status-tab-count count-in-progress">{counts.in_progress}</span>}
        </button>

        <button
          className={`admin-status-tab ${complaintStatusFilter === 'resolved' ? 'active' : ''}`}
          onClick={() => {
            setComplaintStatusFilter('resolved');
            handleFilterChange('resolved', complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
          }}
        >
          <CheckCircle2 size={13} className="text-emerald-400" /> Resolved
          {counts.resolved > 0 && <span className="admin-status-tab-count count-resolved">{counts.resolved}</span>}
        </button>

        <button
          className={`admin-status-tab ${complaintStatusFilter === 'dismissed' ? 'active' : ''}`}
          onClick={() => {
            setComplaintStatusFilter('dismissed');
            handleFilterChange('dismissed', complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter);
          }}
        >
          <XCircle size={13} className="text-slate-400" /> Dismissed
          {counts.dismissed > 0 && <span className="admin-status-tab-count">{counts.dismissed}</span>}
        </button>
      </div>

      <Card style={{ marginTop: 'var(--space-4)' }}>
        <CardHeader style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
          <div>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <AlertCircle className="cm-icon-md text-[var(--cm-accent)]" /> Student Complaints & Maintenance Tickets
            </CardTitle>
            <CardDescription>
              Triage, route to ground staff, and manage complaint lifecycle statuses across all campus hostels and facilities.
            </CardDescription>
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* Category filter */}
            <select
              className="admin-filter-select"
              value={complaintCategoryFilter}
              onChange={(e) => {
                setComplaintCategoryFilter(e.target.value);
                handleFilterChange(complaintStatusFilter, e.target.value, complaintStaffRoleFilter, complaintScopeFilter);
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
              className="admin-filter-select"
              value={complaintStaffRoleFilter}
              onChange={(e) => {
                setComplaintStaffRoleFilter(e.target.value);
                handleFilterChange(complaintStatusFilter, complaintCategoryFilter, e.target.value, complaintScopeFilter);
              }}
            >
              <option value="">All Staff Roles</option>
              <option value="electrical">⚡ Electrical</option>
              <option value="cleaning">🧹 Cleaning Staff</option>
              <option value="maintenance">🛠️ Maintenance</option>
              <option value="mess_manager">🍽️ Mess Manager</option>
              <option value="watchmen">🔒 Security Staff</option>
            </select>

            {/* Scope filter */}
            <select
              className="admin-filter-select"
              value={complaintScopeFilter}
              onChange={(e) => {
                setComplaintScopeFilter(e.target.value);
                handleFilterChange(complaintStatusFilter, complaintCategoryFilter, complaintStaffRoleFilter, e.target.value);
              }}
            >
              <option value="">All Scopes</option>
              <option value="MESS">🍽️ Mess Scope</option>
              <option value="ROOM_SHARED">👥 Room Shared Fixture</option>
              <option value="ROOM_INDIVIDUAL">👤 Personal Room Item</option>
              <option value="COMMON_AREA">🏢 Common / Floor Area</option>
            </select>

            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFilterChange(complaintStatusFilter, complaintCategoryFilter, complaintStaffRoleFilter, complaintScopeFilter)}
              disabled={isLoadingComplaints}
            >
              <RefreshCw className={`cm-icon-sm mr-1 ${isLoadingComplaints ? 'animate-spin' : ''}`} /> Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {isLoadingComplaints ? (
            <div className="admin-empty-state">
              <RefreshCw className="animate-spin cm-icon-lg mx-auto mb-3 text-[var(--cm-accent)]" />
              <p style={{ fontWeight: 500 }}>Loading complaint tickets...</p>
            </div>
          ) : complaints.length === 0 ? (
            <div className="admin-empty-state">
              <CheckCircle2 className="cm-icon-xl mx-auto mb-3 text-emerald-400" />
              <p style={{ fontWeight: 600, fontSize: '15px' }}>No complaints found</p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', marginTop: '4px' }}>
                There are no complaints matching the selected filter criteria.
              </p>
            </div>
          ) : (
            <div className="admin-complaints-list">
              {complaints.map((c) => {
                const catMeta = CATEGORY_META[c.category] || CATEGORY_META.general;
                const CatIcon = catMeta.icon;
                const isUpdating = updatingComplaintId === c.id;

                return (
                  <div key={c.id} className={`admin-ticket-card status-card-${c.status || 'open'}`}>
                    {/* Header Row */}
                    <div className="admin-ticket-header">
                      <div className="admin-ticket-title-row">
                        <div className="admin-ticket-cat-icon" style={{ background: catMeta.bg, color: catMeta.color }}>
                          <CatIcon size={18} />
                        </div>
                        <div>
                          <div className="admin-ticket-title">{c.title}</div>
                          <div className="admin-ticket-chips-row">
                            <StatusBadge status={c.status} />
                            <StaffRoleBadge role={c.staff_role} />
                            <ScopeBadge scope={c.scope} />
                            <span className="admin-ticket-time">
                              <Clock size={11} /> {formatDate(c.created_at)}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Vote Count Badge */}
                      <div className="admin-ticket-votes-pill">
                        <ThumbsUp size={12} />
                        <span>{c.vote_count || 1} {c.vote_count === 1 ? 'vote' : 'votes'}</span>
                      </div>
                    </div>

                    {/* Student & Location Info Row */}
                    <div className="admin-ticket-meta-strip">
                      <div className="admin-ticket-meta-item">
                        <User size={13} className="text-[var(--cm-muted)]" />
                        <span style={{ fontWeight: 600, color: 'var(--cm-fg)' }}>{c.student_name || 'Student'}</span>
                        {c.scholar_id && <span className="admin-ticket-subtle">({c.scholar_id})</span>}
                      </div>

                      {c.hostel_id && (
                        <div className="admin-ticket-meta-item">
                          <Home size={13} className="text-blue-400" />
                          <span>Hostel Linked</span>
                        </div>
                      )}

                      {c.room_number && (
                        <div className="admin-ticket-meta-item">
                          <DoorOpen size={13} className="text-purple-400" />
                          <span>Room {c.room_number}</span>
                        </div>
                      )}

                      {c.mess_id && (
                        <div className="admin-ticket-meta-item">
                          <UtensilsCrossed size={13} className="text-orange-400" />
                          <span>{c.mess_id}</span>
                        </div>
                      )}
                    </div>

                    {/* Complaint Description Body */}
                    <div className="admin-ticket-description">
                      {c.description}
                    </div>

                    {/* ── Structured Ticket Lifecycle Action Toolbar ── */}
                    <div className="admin-ticket-footer">
                      <div className="admin-ticket-id-tag">
                        Ticket ID: <code>{c.id.slice(0, 8)}</code>
                      </div>

                      <div className="admin-ticket-actions-group">
                        {/* ── Status Lifecycle: OPEN ── */}
                        {c.status === 'open' && (
                          <>
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => updateComplaintStatus(c.id, 'in_progress')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              title="Assign to ground staff and start resolution"
                            >
                              <ArrowRight size={13} style={{ marginRight: '4px' }} /> Start Progress
                            </Button>
                            <Button
                              size="xs"
                              onClick={() => updateComplaintStatus(c.id, 'resolved')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              style={{ background: '#10b981', color: '#fff' }}
                            >
                              <CheckCircle2 size={13} style={{ marginRight: '4px' }} /> Resolve
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => updateComplaintStatus(c.id, 'dismissed')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              style={{ color: 'var(--cm-muted)' }}
                              title="Mark as invalid / rejected"
                            >
                              <XCircle size={13} style={{ marginRight: '4px' }} /> Dismiss
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => setComplaintToDelete(c)}
                              style={{ color: 'var(--cm-error)' }}
                              title="Permanently remove ticket from database"
                            >
                              <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                            </Button>
                          </>
                        )}

                        {/* ── Status Lifecycle: IN PROGRESS ── */}
                        {c.status === 'in_progress' && (
                          <>
                            <Button
                              size="xs"
                              onClick={() => updateComplaintStatus(c.id, 'resolved')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              style={{ background: '#10b981', color: '#fff' }}
                            >
                              <CheckCircle2 size={13} style={{ marginRight: '4px' }} /> Mark Resolved
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => updateComplaintStatus(c.id, 'open')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              style={{ color: 'var(--cm-muted)' }}
                              title="Revert back to open queue"
                            >
                              <RotateCcw size={13} style={{ marginRight: '4px' }} /> Revert to Open
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => updateComplaintStatus(c.id, 'dismissed')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              style={{ color: 'var(--cm-muted)' }}
                            >
                              <XCircle size={13} style={{ marginRight: '4px' }} /> Dismiss
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => setComplaintToDelete(c)}
                              style={{ color: 'var(--cm-error)' }}
                            >
                              <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                            </Button>
                          </>
                        )}

                        {/* ── Status Lifecycle: RESOLVED ── */}
                        {c.status === 'resolved' && (
                          <>
                            <div className="admin-ticket-status-note text-emerald-400">
                              <CheckCircle2 size={13} /> Issue Resolved
                            </div>
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => updateComplaintStatus(c.id, 'in_progress')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              title="Reopen ticket if the issue recurred"
                            >
                              <RotateCcw size={13} style={{ marginRight: '4px' }} /> Reopen Ticket
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => setComplaintToDelete(c)}
                              style={{ color: 'var(--cm-error)' }}
                            >
                              <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                            </Button>
                          </>
                        )}

                        {/* ── Status Lifecycle: DISMISSED ── */}
                        {c.status === 'dismissed' && (
                          <>
                            <div className="admin-ticket-status-note text-slate-400">
                              <XCircle size={13} /> Ticket Dismissed / Rejected
                            </div>
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => updateComplaintStatus(c.id, 'open')}
                              isLoading={isUpdating}
                              disabled={isUpdating}
                              title="Reopen ticket into active queue"
                            >
                              <RotateCcw size={13} style={{ marginRight: '4px' }} /> Reopen Ticket
                            </Button>
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => setComplaintToDelete(c)}
                              style={{ color: 'var(--cm-error)' }}
                              title="Permanently remove ticket"
                            >
                              <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                            </Button>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
