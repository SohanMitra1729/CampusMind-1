/**
 * src/pages/ChatPage.jsx — Container Page for Student Chat Dashboard
 */

import { useState } from 'react';
import { Menu } from 'lucide-react';
import Sidebar from '../components/chat/Sidebar';
import MessageList from '../components/chat/MessageList';
import NotificationDrawer from '../components/chat/NotificationDrawer';
import MyComplaintsModal from '../components/chat/MyComplaintsModal';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { useNotifications } from '../hooks/useNotifications';
import { useChat } from '../hooks/useChat';
import { useComplaints } from '../hooks/useComplaints';

export default function ChatPage({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const {
    filteredNotifs,
    unreadCount,
    showNotifications,
    setShowNotifications,
    notifFilter,
    setNotifFilter,
    notifRef,
    markAllRead,
    toggleRead,
  } = useNotifications(user?.id);

  const {
    showMyComplaints,
    setShowMyComplaints,
    myComplaints,
    myComplaintsLoading,
    fetchMyComplaints,
  } = useComplaints(user?.id);

  const {
    messages,
    chatSessions,
    activeChatId,
    input,
    handleInputChange,
    isLoading,
    messagesEndRef,
    chatToDelete,
    setChatToDelete,
    isDeletingChat,
    confirmDeleteChat,
    loadChat,
    handleNewChat,
    handleDeleteChatPrompt,
    handleQuickAction,
    sendMessage,
  } = useChat(user?.id);

  const handleFormSubmit = async (e) => {
    await sendMessage(e);
  };

  return (
    <div className="app-chat-layout">
      <MyComplaintsModal
        showMyComplaints={showMyComplaints}
        setShowMyComplaints={setShowMyComplaints}
        myComplaints={myComplaints}
        myComplaintsLoading={myComplaintsLoading}
      />

      <Sidebar
        user={user}
        chatSessions={chatSessions}
        activeChatId={activeChatId}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        onNewChat={handleNewChat}
        onLoadChat={loadChat}
        onDeleteChat={handleDeleteChatPrompt}
        onOpenMyComplaints={() => { setShowMyComplaints(true); fetchMyComplaints(); }}
        onLogout={onLogout}
      >
        <NotificationDrawer
          showNotifications={showNotifications}
          setShowNotifications={setShowNotifications}
          filteredNotifs={filteredNotifs}
          unreadCount={unreadCount}
          notifFilter={notifFilter}
          setNotifFilter={setNotifFilter}
          notifRef={notifRef}
          onMarkAllRead={markAllRead}
          onToggleRead={toggleRead}
        />
      </Sidebar>

      <ConfirmDialog
        open={Boolean(chatToDelete)}
        onOpenChange={(open) => { if (!open) setChatToDelete(null); }}
        title="Delete Conversation?"
        description={`Are you sure you want to delete "${chatToDelete?.title || 'this conversation'}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="destructive"
        isLoading={isDeletingChat}
        onConfirm={confirmDeleteChat}
      />

      <main className="chat-main">
        <header className="chat-header-bar">
          <button className="sidebar-hamburger-btn" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} />
          </button>
          <div className="chat-header-center">
            <div className="chat-header-title">CampusMind AI</div>
            <div className="chat-header-subtitle">NIT Silchar Knowledge & Complaint Network</div>
          </div>
        </header>

        <MessageList
          messages={messages}
          isLoading={isLoading}
          input={input}
          onInputChange={handleInputChange}
          handleSubmit={handleFormSubmit}
          onQuickAction={handleQuickAction}
          messagesEndRef={messagesEndRef}
        />
      </main>
    </div>
  );
}
