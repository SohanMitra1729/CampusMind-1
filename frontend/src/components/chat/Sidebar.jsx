/**
 * src/components/chat/Sidebar.jsx — Chat History & Navigation Sidebar
 */

import { Plus, MessageSquare, Trash2, LogOut, Sparkles, X } from 'lucide-react';

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
      {sidebarOpen && (
        <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />
      )}

      <aside className={`chat-sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
        <button className="sidebar-close-btn" onClick={() => setSidebarOpen(false)}>
          <X size={20} />
        </button>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
          <Sparkles size={22} className="text-blue-400" />
          <span style={{ fontSize: '1.25rem', fontWeight: 'bold', color: '#f8fafc' }}>CampusMind</span>
        </div>

        <button className="new-chat-btn" onClick={onNewChat}>
          <Plus size={18} /> New Chat
        </button>

        <div style={{ margin: '16px 0 8px', fontSize: '0.75rem', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Navigation & Tools
        </div>
        
        <button className="my-complaints-btn" onClick={onOpenMyComplaints}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <MessageSquare size={16} /> My Complaints
          </div>
        </button>

        <div style={{ margin: '16px 0 8px', fontSize: '0.75rem', fontWeight: 'bold', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Recent Conversations
        </div>

        <div className="chat-history-container">
          {chatSessions.length === 0 ? (
            <div style={{ fontSize: '0.8rem', color: '#64748b', padding: '8px 0' }}>No past conversations</div>
          ) : (
            chatSessions.map((chat) => (
              <div
                key={chat.id}
                className={`chat-history-item ${activeChatId === chat.id ? 'active' : ''}`}
                onClick={() => {
                  onLoadChat(chat.id);
                  setSidebarOpen(false);
                }}
              >
                <MessageSquare size={16} style={{ flexShrink: 0, marginRight: '8px' }} />
                <span className="chat-history-text">{chat.title}</span>
                <button
                  className="chat-delete-btn"
                  onClick={(e) => onDeleteChat(e, chat)}
                  title="Delete chat"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="sidebar-bottom-container">
          <div className="sidebar-profile-row">
            <div className="user-profile-header">
              <div className="user-avatar-circle">
                {user?.name ? user.name.charAt(0).toUpperCase() : '?'}
              </div>
              <div className="user-details">
                <span className="user-name">{user?.name || 'User'}</span>
                <span className="user-scholar">{user?.scholar_id || 'Student'}</span>
              </div>
            </div>
            {children}
          </div>

          <button className="logout-btn" onClick={onLogout} style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
            <LogOut size={16} /> Sign Out
          </button>
        </div>
      </aside>
    </>
  );
}
