import { useState } from 'react';
import { Megaphone, CheckCircle2, AlertCircle, RefreshCw, Trash2, Eye, Calendar, Users, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Textarea } from '../ui/Textarea';
import { Badge } from '../ui/Badge';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogClose } from '../ui/Dialog';

export default function NoticeBroadcast({
  noticeTitle,
  setNoticeTitle,
  noticeContent,
  setNoticeContent,
  isPostingNotice,
  noticeAlert,
  noticeResult,
  handlePostNotice,
  postedNotices,
  isLoadingNotices,
  fetchPostedNotices,
  onDeleteNotice,
  formatDate,
  NOTICE_TYPE_LABELS,
}) {
  const [viewingNotice, setViewingNotice] = useState(null);

  return (
    <div className="admin-tab-content">
      {/* Notice Viewer Modal */}
      <Dialog open={Boolean(viewingNotice)} onOpenChange={(open) => { if (!open) setViewingNotice(null); }}>
        <div style={{ padding: 'var(--space-2)' }}>
          <DialogHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '18px' }}>
                {NOTICE_TYPE_LABELS[viewingNotice?.notice_type]?.icon || '📢'}
              </span>
              <DialogTitle style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
                {viewingNotice?.title}
              </DialogTitle>
            </div>
            <DialogDescription style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap', marginTop: '6px' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--cm-muted)', fontSize: '12px' }}>
                <Calendar size={13} /> {formatDate(viewingNotice?.created_at)}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--cm-muted)', fontSize: '12px' }}>
                <Users size={13} /> {viewingNotice?.is_broadcast ? 'All Campus Students' : `${viewingNotice?.scholar_ids?.length || 0} Targeted Students`}
              </span>
            </DialogDescription>
            <DialogClose onClick={() => setViewingNotice(null)} />
          </DialogHeader>

          <div style={{
            marginTop: 'var(--space-4)',
            padding: 'var(--space-4)',
            backgroundColor: 'rgba(15, 23, 42, 0.6)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--cm-border)',
            maxHeight: '360px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.6,
            fontSize: '13px',
            color: 'var(--cm-fg)'
          }}>
            {viewingNotice?.content}
          </div>

          <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <Button variant="secondary" size="sm" onClick={() => setViewingNotice(null)}>
              Close
            </Button>
          </div>
        </div>
      </Dialog>

      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Megaphone className="cm-icon-md text-[var(--cm-accent)]" /> Create Notice Broadcast
          </CardTitle>
          <CardDescription>
            Post official notices — automatically classified, broadcasted to student inboxes, and indexed into vector RAG memory.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {noticeAlert && (
            <div className={`auth-alert-box ${noticeAlert.type === 'success' ? 'auth-alert-success' : 'auth-alert-error'}`} style={{ marginBottom: 'var(--space-4)' }}>
              {noticeAlert.type === 'success' ? <CheckCircle2 className="cm-icon-md flex-shrink-0" /> : <AlertCircle className="cm-icon-md flex-shrink-0" />}
              <span>{noticeAlert.text}</span>
            </div>
          )}

          <form onSubmit={handlePostNotice} className="admin-form">
            <div className="auth-input-group">
              <label className="auth-label">Notice Title</label>
              <Input
                type="text"
                placeholder="e.g. An Appeal to the Entire Student Fraternity - LAN Advisory"
                value={noticeTitle}
                onChange={(e) => setNoticeTitle(e.target.value)}
                required
              />
            </div>

            <div className="auth-input-group" style={{ marginTop: 'var(--space-3)' }}>
              <label className="auth-label">Notice Content</label>
              <Textarea
                placeholder="Enter full notice text..."
                value={noticeContent}
                onChange={(e) => setNoticeContent(e.target.value)}
                rows={6}
                required
              />
            </div>

            <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'flex-end' }}>
              <Button type="submit" isLoading={isPostingNotice} disabled={isPostingNotice || !noticeTitle.trim() || !noticeContent.trim()}>
                Post Notice Broadcast
              </Button>
            </div>
          </form>

          {noticeResult && (
            <div className="admin-agent-report-card" style={{ borderColor: 'rgba(59, 130, 246, 0.3)', marginTop: 'var(--space-4)' }}>
              <div className="admin-agent-report-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CheckCircle2 className="cm-icon-sm text-emerald-400" />
                  <span style={{ fontWeight: 600, fontSize: '13px' }}>Broadcast & Ingestion Execution Summary</span>
                </div>
                <span className="admin-agent-report-badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', borderColor: 'rgba(59, 130, 246, 0.3)' }}>
                  Active Notice
                </span>
              </div>

              <div className="admin-agent-report-grid">
                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Category</span>
                  <span className="admin-agent-field-val" style={{ textTransform: 'capitalize' }}>
                    {noticeResult.icon} {noticeResult.notice_type || 'General'}
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Audience Scope</span>
                  <span className="admin-agent-field-val">
                    {noticeResult.is_broadcast ? '🌐 All Students (Broadcast)' : `🎯 Targeted (${noticeResult.scholar_ids_found?.length || 0} Scholars)`}
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Students Alerted</span>
                  <span className="admin-agent-field-val" style={{ color: '#4ade80', fontWeight: 700 }}>
                    {noticeResult.students_notified ?? noticeResult.notified_count ?? 0} notified
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">RAG Knowledge Base</span>
                  <span className="admin-agent-field-val" style={{ color: 'var(--cm-accent)' }}>
                    {noticeResult.rag_chunks_indexed || 1} chunk(s) indexed
                  </span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card style={{ marginTop: 'var(--space-6)' }}>
        <CardHeader style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <Megaphone className="cm-icon-md text-[var(--cm-accent)]" /> Recent Broadcasts ({postedNotices.length})
            </CardTitle>
            <CardDescription>History of posted notices, audience distribution, and delivered alerts.</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchPostedNotices}>
            <RefreshCw className={`cm-icon-sm mr-1 ${isLoadingNotices ? 'animate-spin' : ''}`} /> Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoadingNotices ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              <RefreshCw className="animate-spin cm-icon-md mx-auto mb-2" /> Loading notices...
            </div>
          ) : postedNotices.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              No notices broadcasted yet.
            </div>
          ) : (
            <div className="admin-table-wrapper" style={{ overflowX: 'auto' }}>
              <table className="admin-table" style={{ width: '100%', borderCollapse: 'separate', borderSpacing: '0' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '12px 16px', textAlign: 'left', minWidth: '240px' }}>Notice Title</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', minWidth: '140px' }}>Category</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', minWidth: '150px' }}>Targeting</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', minWidth: '110px' }}>Delivered</th>
                    <th style={{ padding: '12px 16px', textAlign: 'left', minWidth: '140px' }}>Posted At</th>
                    <th style={{ padding: '12px 16px', textAlign: 'right', minWidth: '130px' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {postedNotices.map((n) => {
                    const typeConfig = NOTICE_TYPE_LABELS[n.notice_type] || NOTICE_TYPE_LABELS.general;
                    return (
                      <tr key={n.id} style={{ borderBottom: '1px solid var(--cm-border)' }}>
                        <td style={{ padding: '12px 16px', fontWeight: 600, color: 'var(--cm-fg)' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <FileText size={15} className="text-blue-400 flex-shrink-0" />
                            <span>{n.title}</span>
                          </div>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 9px',
                            borderRadius: '9999px',
                            fontSize: '11px',
                            fontWeight: 500,
                            backgroundColor: 'rgba(51, 65, 85, 0.4)',
                            border: '1px solid rgba(100, 116, 139, 0.3)',
                            color: 'var(--cm-fg)'
                          }}>
                            {typeConfig.icon} {typeConfig.label}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '4px',
                            padding: '3px 8px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 500,
                            backgroundColor: n.is_broadcast ? 'rgba(59, 130, 246, 0.12)' : 'rgba(168, 85, 247, 0.12)',
                            color: n.is_broadcast ? '#93c5fd' : '#d8b4fe',
                            border: `1px solid ${n.is_broadcast ? 'rgba(59, 130, 246, 0.25)' : 'rgba(168, 85, 247, 0.25)'}`
                          }}>
                            {n.is_broadcast ? '🌐 All Students' : `🎯 ${n.scholar_ids?.length || 0} Scholars`}
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px' }}>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            padding: '2px 8px',
                            borderRadius: '6px',
                            fontSize: '11px',
                            fontWeight: 600,
                            backgroundColor: 'rgba(16, 185, 129, 0.12)',
                            color: '#4ade80',
                            border: '1px solid rgba(16, 185, 129, 0.25)'
                          }}>
                            {n.notified_count || 0} users
                          </span>
                        </td>
                        <td style={{ padding: '12px 16px', fontSize: '12px', color: 'var(--cm-muted)', whiteSpace: 'nowrap' }}>
                          {formatDate(n.created_at)}
                        </td>
                        <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                            <Button
                              variant="secondary"
                              size="xs"
                              onClick={() => setViewingNotice(n)}
                              title="View full notice content"
                            >
                              <Eye size={13} style={{ marginRight: '4px' }} /> View
                            </Button>
                            {onDeleteNotice && (
                              <Button
                                variant="ghost"
                                size="xs"
                                onClick={() => onDeleteNotice(n)}
                                style={{ color: 'var(--cm-error)' }}
                                title="Delete notice broadcast and vector chunks"
                              >
                                <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                              </Button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
