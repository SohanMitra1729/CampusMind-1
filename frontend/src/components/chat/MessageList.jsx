/**
 * src/components/chat/MessageList.jsx — Messages Feed, Quick Actions & RAG Sources
 */

import ReactMarkdown from 'react-markdown';
import { Sparkles, Loader2, Calendar, Home, BellRing, AlertCircle, CheckCircle2, Send } from 'lucide-react';

export default function MessageList({
  messages,
  isLoading,
  input,
  onInputChange,
  handleSubmit,
  onQuickAction,
  messagesEndRef,
}) {
  return (
    <div className="chat-messages-scroll">
      <div className="chat-messages-inner">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <div className="chat-empty-logo">
              <Sparkles size={36} />
            </div>
            <h1 className="chat-empty-title">Welcome to CampusMind</h1>
            <p className="chat-empty-desc">
              Your intelligent campus AI assistant for knowledge, notices, and complaints.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`chat-bubble-row ${msg.role === 'user' ? 'user' : 'bot'}`}>
            <div className={`chat-bubble ${msg.role === 'user' ? 'user' : 'bot'}`}>
              <div style={{ fontSize: '0.75rem', fontWeight: 'bold', marginBottom: '4px', opacity: 0.8 }}>
                {msg.role === 'user' ? 'You' : 'CampusMind AI'}
              </div>
              {msg.role === 'bot' ? (
                <div className="chat-bubble-markdown">
                  {!msg.content && isLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--cm-muted)', fontSize: '0.875rem' }}>
                      <Loader2 className="animate-spin cm-icon-sm" /> Thinking...
                    </div>
                  ) : (
                    <ReactMarkdown
                      disallowedElements={['script', 'iframe', 'object']}
                      unwrapDisallowed
                    >
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>
              ) : (
                <p style={{ margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {msg.content}
                </p>
              )}

              {msg.metadata?.sources && msg.metadata.sources.length > 0 && (
                <div className="chat-sources">
                  <span style={{ fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', color: 'var(--cm-muted)' }}>
                    Sources consulted:
                  </span>
                  {msg.metadata.sources.map((src, i) => (
                    <div key={i} className="chat-source-item">
                      <span className="chat-source-badge">
                        📄 {src.source || 'Document'} {src.page ? `(p. ${src.page})` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}


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
            onChange={(e) => onInputChange(e.target.value)}
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
