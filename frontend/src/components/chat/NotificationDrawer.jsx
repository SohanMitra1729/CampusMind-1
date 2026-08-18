import { useState } from 'react';
import { Bell, Calendar, Info, Megaphone, FileText, ExternalLink, Download } from 'lucide-react';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogClose } from '../ui/Dialog';
import { Button } from '../ui/Button';
import { API_BASE_URL } from '../../api/client';

export default function NotificationDrawer({
  showNotifications,
  setShowNotifications,
  filteredNotifs,
  unreadCount,
  notifFilter,
  setNotifFilter,
  notifRef,
  onMarkAllRead,
  onToggleRead,
}) {
  const [selectedNotif, setSelectedNotif] = useState(null);

  const handleNotifClick = (n) => {
    onToggleRead(n.id);
    setSelectedNotif(n);
  };

  const isPdfNotice = selectedNotif?.source_type === 'pdf' || Boolean(selectedNotif?.source_file);
  const pdfFilename = selectedNotif?.source_file || (selectedNotif?.title?.endsWith('.pdf') ? selectedNotif?.title : null);

  const handleOpenPdf = () => {
    if (!pdfFilename) return;
    const pdfUrl = `${API_BASE_URL}/api/documents/${encodeURIComponent(pdfFilename)}/view`;
    window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  };

  const formatDate = (iso) => {
    if (!iso) return selectedNotif?.time || 'Recent';
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <>
      {/* Student Notification Detail Modal */}
      <Dialog open={Boolean(selectedNotif)} onOpenChange={(open) => { if (!open) setSelectedNotif(null); }}>
        <div style={{ padding: 'var(--space-2)' }}>
          <DialogHeader>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '18px' }}>
                {isPdfNotice ? '📄' : (selectedNotif?.icon || '📢')}
              </span>
              <DialogTitle style={{ fontSize: '1.1rem', fontWeight: 700, margin: 0 }}>
                {selectedNotif?.notice_title || selectedNotif?.title || 'Notice Notification'}
              </DialogTitle>
            </div>
            <DialogDescription style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '6px', flexWrap: 'wrap' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--cm-muted)', fontSize: '12px' }}>
                <Calendar size={13} /> {formatDate(selectedNotif?.created_at)}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: 'var(--cm-muted)', fontSize: '12px' }}>
                <Megaphone size={13} /> {selectedNotif?.is_broadcast !== false ? 'All Campus Students' : 'Targeted Notice'}
              </span>
              {isPdfNotice && (
                <span style={{
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  color: '#60a5fa',
                  border: '1px solid rgba(59, 130, 246, 0.3)'
                }}>
                  Official PDF Attachment
                </span>
              )}
            </DialogDescription>
            <DialogClose onClick={() => setSelectedNotif(null)} />
          </DialogHeader>

          {/* If notice has a PDF attached, show prominent PDF Action Card */}
          {isPdfNotice && pdfFilename && (
            <div style={{
              marginTop: 'var(--space-3)',
              padding: 'var(--space-3) var(--space-4)',
              backgroundColor: 'rgba(30, 41, 59, 0.7)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid rgba(59, 130, 246, 0.35)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#f87171',
                  flexShrink: 0
                }}>
                  <FileText size={18} />
                </div>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--cm-fg)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {pdfFilename}
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--cm-muted)' }}>
                    Official PDF Document
                  </div>
                </div>
              </div>

              <Button
                size="sm"
                onClick={handleOpenPdf}
                style={{
                  background: 'linear-gradient(135deg, #3b82f6, #2563eb)',
                  color: '#ffffff',
                  fontWeight: 600,
                  flexShrink: 0,
                  boxShadow: '0 2px 8px rgba(37, 99, 235, 0.3)'
                }}
              >
                <ExternalLink size={14} style={{ marginRight: '6px' }} /> Open PDF
              </Button>
            </div>
          )}

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
            {selectedNotif?.notice_content || selectedNotif?.message}
          </div>

          <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
            <Button variant="secondary" size="sm" onClick={() => setSelectedNotif(null)}>
              Close
            </Button>
          </div>
        </div>
      </Dialog>

      <div style={{ position: 'relative' }} ref={notifRef}>
        <button
          className="chat-delete-btn"
          style={{ padding: 'var(--space-2)', position: 'relative', opacity: 1 }}
          onClick={() => setShowNotifications(!showNotifications)}
          title="Notifications"
        >
          <Bell className="cm-icon-md text-[var(--cm-fg)]" />
          {unreadCount > 0 && (
            <span style={{ position: 'absolute', top: 0, right: 0, width: '10px', height: '10px', backgroundColor: 'var(--cm-error)', borderRadius: 'var(--radius-full)', border: '2px solid var(--cm-bg)' }}></span>
          )}
        </button>

        {showNotifications && (
          <div className="cm-dropdown-content" style={{ position: 'absolute', bottom: 'calc(100% + 10px)', left: '-20px', width: '320px', padding: 0, backgroundColor: 'var(--cm-bg)', border: '1px solid var(--cm-border)', borderRadius: 'var(--radius-lg)', boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)', zIndex: 50 }}>
            <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--cm-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontWeight: 'var(--font-semibold)', fontSize: '13px' }}>Notifications</span>
              <div style={{ display: 'flex', gap: 'var(--space-2)', fontSize: 'var(--text-xs)' }}>
                <button type="button" onClick={() => setNotifFilter('all')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: notifFilter === 'all' ? 'bold' : 'normal', color: notifFilter === 'all' ? 'var(--cm-accent)' : 'var(--cm-muted)' }}>All</button>
                <button type="button" onClick={() => setNotifFilter('unread')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: notifFilter === 'unread' ? 'bold' : 'normal', color: notifFilter === 'unread' ? 'var(--cm-accent)' : 'var(--cm-muted)' }}>Unread ({unreadCount})</button>
              </div>
              {unreadCount > 0 && (
                <button type="button" onClick={onMarkAllRead} style={{ background: 'transparent', border: 'none', color: 'var(--cm-accent)', fontSize: 'var(--text-xs)', cursor: 'pointer' }}>Mark all read</button>
              )}
            </div>
            <div style={{ maxHeight: '320px', overflowY: 'auto' }}>
              {filteredNotifs.length === 0 ? (
                <div style={{ padding: 'var(--space-6)', textAlign: 'center', color: 'var(--cm-muted)', fontSize: 'var(--text-sm)' }}>
                  <Bell className="cm-icon-md mx-auto mb-2 text-slate-500" />
                  No new notifications
                </div>
              ) : (
                filteredNotifs.map(n => (
                  <div
                    key={n.id}
                    style={{
                      padding: 'var(--space-3)',
                      borderBottom: '1px solid var(--cm-border)',
                      cursor: 'pointer',
                      backgroundColor: n.unread ? 'rgba(30, 41, 59, 0.5)' : 'transparent',
                      transition: 'background-color 0.15s ease'
                    }}
                    onClick={() => handleNotifClick(n)}
                    onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(51, 65, 85, 0.4)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = n.unread ? 'rgba(30, 41, 59, 0.5)' : 'transparent'; }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--cm-fg)' }}>
                        {n.icon || '📢'} {n.title}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--cm-muted)', whiteSpace: 'nowrap' }}>{n.time}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--cm-muted)', lineHeight: 1.4 }}>
                      {n.message}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
