/**
 * src/components/chat/NotificationDrawer.jsx — Notifications Popover & Filter Tabs
 */

import { Bell } from 'lucide-react';

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
  return (
    <div style={{ position: 'relative' }} ref={notifRef}>
      <button
        className="chat-delete-btn"
        style={{ padding: 'var(--space-2)', position: 'relative', opacity: 1 }}
        onClick={() => setShowNotifications(!showNotifications)}
      >
        <Bell className="cm-icon-md text-[var(--cm-fg)]" />
        {unreadCount > 0 && (
          <span style={{ position: 'absolute', top: 0, right: 0, width: '10px', height: '10px', backgroundColor: 'var(--cm-error)', borderRadius: 'var(--radius-full)', border: '2px solid var(--cm-bg)' }}></span>
        )}
      </button>

      {showNotifications && (
        <div className="cm-dropdown-content" style={{ position: 'absolute', bottom: 'calc(100% + 10px)', left: '-20px', width: '300px', padding: 0, backgroundColor: 'var(--cm-bg)', border: '1px solid var(--cm-border)', borderRadius: 'var(--radius-lg)' }}>
          <div style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--cm-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 'var(--font-semibold)' }}>Notifications</span>
            <div style={{ display: 'flex', gap: 'var(--space-2)', fontSize: 'var(--text-xs)' }}>
              <button type="button" onClick={() => setNotifFilter('all')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: notifFilter === 'all' ? 'bold' : 'normal', color: notifFilter === 'all' ? 'var(--cm-accent)' : 'var(--cm-muted)' }}>All</button>
              <button type="button" onClick={() => setNotifFilter('unread')} style={{ background: 'none', border: 'none', cursor: 'pointer', fontWeight: notifFilter === 'unread' ? 'bold' : 'normal', color: notifFilter === 'unread' ? 'var(--cm-accent)' : 'var(--cm-muted)' }}>Unread ({unreadCount})</button>
            </div>
            {unreadCount > 0 && (
              <button type="button" onClick={onMarkAllRead} style={{ background: 'transparent', border: 'none', color: 'var(--cm-accent)', fontSize: 'var(--text-xs)', cursor: 'pointer' }}>Mark all read</button>
            )}
          </div>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            {filteredNotifs.length === 0 ? (
              <div style={{ padding: 'var(--space-4)', textAlign: 'center', color: 'var(--cm-muted)', fontSize: 'var(--text-sm)' }}>No new notifications</div>
            ) : (
              filteredNotifs.map(n => (
                <div key={n.id} style={{ padding: 'var(--space-3)', borderBottom: '1px solid var(--cm-border)', cursor: 'pointer', backgroundColor: n.unread ? 'var(--cm-secondary)' : 'transparent' }} onClick={() => onToggleRead(n.id)}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)' }}>
                    <span style={{ fontWeight: 'var(--font-medium)', fontSize: 'var(--text-sm)' }}>{n.title}</span>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)' }}>{n.time}</span>
                  </div>
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)' }}>{n.message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
