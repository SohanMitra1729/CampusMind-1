/**
 * src/components/admin/NoticeBroadcast.jsx — Post Notices & Broadcast History
 */

import { Megaphone, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Textarea } from '../ui/Textarea';
import { Badge } from '../ui/Badge';

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
  formatDate,
  NOTICE_TYPE_LABELS,
}) {
  return (
    <div className="admin-tab-content">
      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Megaphone className="cm-icon-md text-[var(--cm-accent)]" /> Create Notice Broadcast
          </CardTitle>
          <CardDescription>
            Post official notices — automatically analyzed by Gemini agent to extract target students & trigger Telegram alerts.
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
                placeholder="e.g. End Semester Exam Schedule 2026"
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

          {noticeResult && noticeResult.agent_result && (
            <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', background: 'var(--cm-secondary)', border: '1px solid var(--cm-border)', fontSize: 'var(--text-xs)' }}>
              <div style={{ fontWeight: 'var(--font-semibold)', marginBottom: 'var(--space-1)' }}>🤖 Agent Execution Summary</div>
              <div>Type: <strong>{noticeResult.agent_result.notice_type || 'general'}</strong></div>
              <div>Broadcast: <strong>{noticeResult.agent_result.is_broadcast ? 'Yes (All Students)' : 'Targeted'}</strong></div>
              <div>Students Notified: <strong>{noticeResult.notified_count || 0}</strong></div>
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
            <CardDescription>History of posted notices and delivery counts.</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchPostedNotices}>
            <RefreshCw className="cm-icon-sm mr-1" /> Refresh
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
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Targeting</th>
                    <th>Notified</th>
                    <th>Posted At</th>
                  </tr>
                </thead>
                <tbody>
                  {postedNotices.map((n) => {
                    const typeConfig = NOTICE_TYPE_LABELS[n.notice_type] || NOTICE_TYPE_LABELS.general;
                    return (
                      <tr key={n.id}>
                        <td style={{ fontWeight: 'var(--font-medium)' }}>{n.title}</td>
                        <td>
                          <Badge variant="secondary">
                            {typeConfig.icon} {typeConfig.label}
                          </Badge>
                        </td>
                        <td>{n.is_broadcast ? '🌐 All Students' : `🎯 ${n.scholar_ids?.length || 0} Scholars`}</td>
                        <td>{n.notified_count || 0} users</td>
                        <td>{formatDate(n.created_at)}</td>
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
