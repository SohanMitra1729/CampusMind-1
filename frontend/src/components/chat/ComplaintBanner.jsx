/**
 * src/components/chat/ComplaintBanner.jsx — Complaint Confirmation & Similar Complaints Upvoting
 */

import { AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from '../ui/Button';

export default function ComplaintBanner({
  complaintPending,
  setComplaintPending,
  hostels,
  selectedHostelId,
  setSelectedHostelId,
  roomNumber,
  setRoomNumber,
  onSubmitComplaint,
  complaintSubmitting,
  complaintResult,
  onVote,
  votedComplaints,
}) {
  if (!complaintPending && !complaintResult) return null;

  return (
    <>
      {complaintPending && !complaintResult && (
        <div className="chat-complaint-banner">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)' }}>
            <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
              <AlertCircle className="cm-icon-lg text-amber-500" />
              <div>
                <div style={{ fontWeight: 'var(--font-semibold)', color: 'var(--cm-fg)' }}>File a formal complaint?</div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--cm-muted)' }}>
                  We detected an issue regarding: <strong style={{ color: 'var(--cm-fg)' }}>{complaintPending.category}</strong>
                </div>
              </div>
            </div>
            <button onClick={() => setComplaintPending(null)} style={{ background: 'transparent', border: 'none', color: 'var(--cm-muted)', cursor: 'pointer' }}>✕</button>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', marginBottom: 'var(--space-4)' }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ display: 'block', fontSize: 'var(--text-xs)', fontWeight: 'var(--font-medium)', marginBottom: 'var(--space-1)', color: 'var(--cm-muted)' }}>Hostel</label>
              <select
                style={{ width: '100%', padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', outline: 'none' }}
                value={selectedHostelId}
                onChange={e => setSelectedHostelId(e.target.value)}
              >
                <option value="">Select hostel…</option>
                {hostels.map(h => (
                  <option key={h.id} value={h.id}>{h.code} – {h.name}</option>
                ))}
              </select>
            </div>

            {complaintPending.needsRoom && (
              <div style={{ flex: '1 1 200px' }}>
                <label style={{ display: 'block', fontSize: 'var(--text-xs)', fontWeight: 'var(--font-medium)', marginBottom: 'var(--space-1)', color: 'var(--cm-muted)' }}>Room Number</label>
                <input
                  style={{ width: '100%', padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', outline: 'none' }}
                  type="text"
                  placeholder="e.g. 204"
                  value={roomNumber}
                  onChange={e => setRoomNumber(e.target.value)}
                  maxLength={10}
                />
              </div>
            )}
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <Button onClick={onSubmitComplaint} disabled={complaintSubmitting || !selectedHostelId || (complaintPending.needsRoom && !roomNumber.trim())} isLoading={complaintSubmitting}>
              Submit Complaint
            </Button>
            <Button variant="ghost" onClick={() => setComplaintPending(null)}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {complaintResult && !complaintResult.error && (
        <div className="chat-complaint-banner" style={{ background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.2)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            <CheckCircle2 className="cm-icon-lg text-emerald-500" />
            <div>
              <div style={{ fontWeight: 'var(--font-semibold)', color: 'var(--cm-fg)' }}>Complaint Submitted successfully!</div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--cm-muted)' }}>{complaintResult.title}</div>
            </div>
          </div>
          {complaintResult.similar_complaints?.length > 0 && (
            <div style={{ marginTop: 'var(--space-3)', borderTop: '1px solid rgba(16,185,129,0.2)', paddingTop: 'var(--space-2)' }}>
              <div style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-medium)', marginBottom: 'var(--space-2)' }}>Similar Open Complaints:</div>
              {complaintResult.similar_complaints.map(s => (
                <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 'var(--text-xs)', marginBottom: '4px' }}>
                  <span>{s.title} ({s.vote_count} votes)</span>
                  <Button size="xs" variant="secondary" onClick={() => onVote(s.id)} disabled={votedComplaints.has(s.id)}>
                    {votedComplaints.has(s.id) ? 'Voted 👍' : 'Upvote +1'}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {complaintResult?.error && (
        <div className="chat-complaint-banner" style={{ background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.2)' }}>
          <div style={{ fontWeight: 'var(--font-semibold)', color: 'var(--cm-error)' }}>Submission Failed</div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--cm-muted)' }}>{complaintResult.error}</div>
        </div>
      )}
    </>
  );
}
