/**
 * src/pages/ChatPage.jsx — Container Page for Student Chat Dashboard
 */

import { useState } from 'react';
import Sidebar from '../components/chat/Sidebar';
import MessageList from '../components/chat/MessageList';
import ComplaintBanner from '../components/chat/ComplaintBanner';
import NotificationDrawer from '../components/chat/NotificationDrawer';
import MyComplaintsModal from '../components/chat/MyComplaintsModal';
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
    hostels,
    complaintPending,
    setComplaintPending,
    complaintSubmitting,
    complaintResult,
    votedComplaints,
    selectedHostelId,
    setSelectedHostelId,
    roomNumber,
    setRoomNumber,
    showMyComplaints,
    setShowMyComplaints,
    myComplaints,
    myComplaintsLoading,
    detectComplaint,
    fetchMyComplaints,
    submitComplaint,
    upvoteComplaint,
    resetComplaintState,
  } = useComplaints(user?.id);

  const {
    messages,
    chatSessions,
    activeChatId,
    input,
    setInput,
    handleInputChange,
    isLoading,
    messagesEndRef,
    loadChat,
    handleNewChat,
    handleDeleteChat,
    handleQuickAction,
    sendMessage,
  } = useChat(user?.id, detectComplaint);

  const handleFormSubmit = async (e) => {
    resetComplaintState();
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
        onDeleteChat={handleDeleteChat}
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

      <main className="chat-main">
        <ComplaintBanner
          complaintPending={complaintPending}
          setComplaintPending={setComplaintPending}
          hostels={hostels}
          selectedHostelId={selectedHostelId}
          setSelectedHostelId={setSelectedHostelId}
          roomNumber={roomNumber}
          setRoomNumber={setRoomNumber}
          onSubmitComplaint={submitComplaint}
          complaintSubmitting={complaintSubmitting}
          complaintResult={complaintResult}
          onVote={upvoteComplaint}
          votedComplaints={votedComplaints}
        />

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
