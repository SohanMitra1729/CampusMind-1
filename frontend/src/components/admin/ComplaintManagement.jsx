/**
 * src/components/admin/ComplaintManagement.jsx — Complaints Admin Table & Status Action Buttons
 */

import { AlertCircle, RefreshCw, Users, User as UserIcon } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

export default function ComplaintManagement({
  complaints,
  isLoadingComplaints,
  complaintStatusFilter,
  setComplaintStatusFilter,
  complaintCategoryFilter,
  setComplaintCategoryFilter,
  fetchComplaints,
  updateComplaintStatus,
  updatingComplaintId,
  formatDate,
}) {
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

          <div style={{ display: 'flex', gap: 'var(--space-2)', flexWrap: 'wrap' }}>
            <select
              style={{ padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', fontSize: 'var(--text-xs)' }}
              value={complaintStatusFilter}
              onChange={(e) => {
                setComplaintStatusFilter(e.target.value);
                fetchComplaints(e.target.value, complaintCategoryFilter);
              }}
            >
              <option value="">All Statuses</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="resolved">Resolved</option>
              <option value="dismissed">Dismissed</option>
            </select>

            <select
              style={{ padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', fontSize: 'var(--text-xs)' }}
              value={complaintCategoryFilter}
              onChange={(e) => {
                setComplaintCategoryFilter(e.target.value);
                fetchComplaints(complaintStatusFilter, e.target.value);
              }}
            >
              <option value="">All Categories</option>
              <option value="hostel">Hostel</option>
              <option value="academic">Academic</option>
              <option value="facility">Facility</option>
              <option value="mess">Mess</option>
              <option value="general">General</option>
            </select>

            <Button variant="ghost" size="sm" onClick={() => fetchComplaints(complaintStatusFilter, complaintCategoryFilter)}>
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
                    <div className="admin-complaint-header-row">
                      <div className="flex gap-3">
                        <div className="text-2xl mt-1">{c.category_icon}</div>
                        <div>
                          <div className="font-semibold text-lg mb-1">{c.title}</div>
                          <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--cm-muted)]">
                            <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                              {c.status === 'open' ? 'Open' : c.status === 'in_progress' ? 'In Progress' : c.status === 'resolved' ? 'Resolved' : 'Dismissed'}
                            </Badge>
                            <span className="flex items-center gap-1"><UserIcon className="cm-icon-xs" /> {c.student_name} ({c.scholar_id})</span>
                            <span className="flex items-center gap-1"><Users className="cm-icon-xs" /> {c.vote_count} votes</span>
                            <span>{formatDate(c.created_at)}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <p className="mt-4 text-sm text-[var(--cm-fg)] leading-relaxed">
                      {c.description}
                    </p>

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
