/**
 * src/components/chat/Sidebar.jsx — Chat History & Navigation Sidebar
 */

import { Plus, MessageSquare, Trash2, LogOut, ChevronDown, Menu, X } from 'lucide-react';
import { Button } from '../ui/Button';

export default function Sidebar({
  user,
  chatSessions,
  activeChatId,
  sidebarOpen,
  setSidebarOpen,
  onNewChat,
  onLoadChat,
  onDeleteChat,
  onOpenMyComplaints,
  onLogout,
  children, // Notification drawer portal
}) {
  return (
    <>
      <button className="chat-mobile-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      <aside className={`chat-sidebar ${sidebarOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          <div className="sidebar-logo">
            <span className="logo-sparkle">✨</span>
            <span className="logo-text">CampusMind</span>
          </div>
          <Button variant="secondary" className="new-chat-btn" onClick={onNewChat}>
            <Plus size={18} /> New Chat
          </Button>
        </div>

        <div className="sidebar-section-title">Navigation & Tools</div>
        <div className="sidebar-history-list" style={{ flex: '0 0 auto', paddingBottom: 0 }}>
          <button className="history-item" onClick={onOpenMyComplaints}>
            <MessageSquare size={16} /> My Complaints
          </button>
        </div>

        <div className="sidebar-section-title" style={{ marginTop: 'var(--space-4)' }}>Recent Conversations</div>
        <div className="sidebar-history-list">
          {chatSessions.length === 0 ? (
            <div className="history-empty">No past conversations</div>
          ) : (
            chatSessions.map((chat) => (
              <div
                key={chat.id}
                className={`history-item ${activeChatId === chat.id ? 'active' : ''}`}
                onClick={() => onLoadChat(chat.id)}
              >
                <MessageSquare size={16} />
                <span className="history-title">{chat.title}</span>
                <button
                  className="history-delete-btn"
                  onClick={(e) => onDeleteChat(e, chat.id)}
                  title="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-profile-row">
          <div className="user-profile-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <div className="user-avatar-circle">
                {user?.name ? user.name.charAt(0) : '?'}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 'var(--font-medium)', whiteSpace: 'nowrap' }}>
                {user?.name || 'User'}
              </div>
            </div>
            <ChevronDown className="cm-icon-sm text-[var(--cm-muted)]" />
          </div>

          {children}

          <Button
            variant="ghost"
            size="sm"
            onClick={onLogout}
            style={{ width: '100%', marginTop: 'var(--space-2)', color: 'var(--cm-error)' }}
          >
            <LogOut size={16} style={{ marginRight: '8px' }} /> Sign Out
          </Button>
        </div>
      </aside>
    </>
  );
}
