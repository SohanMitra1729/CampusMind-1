/**
 * src/components/chat/MessageList.jsx — Messages Feed, Quick Actions & RAG Sources
 */

import { Sparkles, User as UserIcon, Loader2, Calendar, Home, BellRing, AlertCircle, CheckCircle2, Paperclip, Send } from 'lucide-react';
import { Badge } from '../ui/Badge';

export default function MessageList({
  messages,
  isLoading,
  input,
  setInput,
  handleSubmit,
  onQuickAction,
  messagesEndRef,
}) {
  return (
    <div className="chat-messages-scroll-area">
      <div className="chat-messages-container">
        {messages.length === 0 && (
          <div className="chat-welcome-hero">
            <div className="welcome-icon-hero">✨</div>
            <h1>Welcome to CampusMind</h1>
            <p>Your intelligent campus AI assistant for knowledge, notices, and complaints.</p>
          </div>
        )}

        {messages.map((msg, index) => (
          <div key={index} className={`chat-message-row ${msg.role === 'user' ? 'user-row' : 'bot-row'}`}>
            <div className="message-avatar">
              {msg.role === 'user' ? <UserIcon size={18} /> : <Sparkles size={18} />}
            </div>
            <div className="message-content-box">
              <div className="message-author">{msg.role === 'user' ? 'You' : 'CampusMind AI'}</div>
              <div className="message-text">{msg.content}</div>

              {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                <div className="message-sources-box">
                  <div className="sources-title">Sources consulted:</div>
                  <div className="sources-list">
                    {msg.metadata.sources.map((src, i) => (
                      <Badge key={i} variant="secondary" className="source-badge">
                        📄 {src.source || 'Document'} {src.page ? `(p. ${src.page})` : ''}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="chat-message-row bot-row">
            <div className="message-avatar">
              <Sparkles size={18} />
            </div>
            <div className="message-content-box">
              <div className="message-author">CampusMind AI</div>
              <div className="thinking-indicator">
                <Loader2 className="animate-spin cm-icon-sm" /> Thinking...
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        {messages.length === 0 && !isLoading && (
          <div className="quick-actions-grid">
            <button className="qa-card" type="button" onClick={() => onQuickAction('Show me the academic calendar', 'academic')}>
              <Calendar className="qa-icon" />
              <div className="qa-text">Academic Calendar</div>
            </button>
            <button className="qa-card" type="button" onClick={() => onQuickAction('I want to report an issue with my hostel', 'hostel')}>
              <Home className="qa-icon" />
              <div className="qa-text">Hostel Information</div>
            </button>
            <button className="qa-card" type="button" onClick={() => onQuickAction('Are there any new notices?', 'notices')}>
              <BellRing className="qa-icon" />
              <div className="qa-text">Notices &<br />Announcements</div>
            </button>
            <button className="qa-card" type="button" onClick={() => onQuickAction('I want to report an issue', 'hostel')}>
              <AlertCircle className="qa-icon" />
              <div className="qa-text">Report an<br />Issue</div>
            </button>
          </div>
        )}
        <form className="chat-input-wrapper" onSubmit={handleSubmit}>
          <textarea
            className="chat-input-field"
            placeholder="Ask CampusMind anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e);
              }
            }}
            rows={1}
            disabled={isLoading}
          />
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button type="button" className="chat-attach-btn"><Paperclip size={20} /></button>
            <button
              type="submit"
              className="chat-send-btn"
              disabled={isLoading || !input.trim()}
            >
              <Send size={18} />
            </button>
          </div>
        </form>
        <div style={{ textAlign: 'center', marginTop: '16px', fontSize: '0.7rem', color: '#94a3b8', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '4px' }}>
          <CheckCircle2 size={12} /> CampusMind can make mistakes. Consider verifying important information.
        </div>
      </div>
    </div>
  );
}
