import React, { useState, useRef, useEffect } from 'react';
import { Plus, MessageSquare, Trash2, Send, Loader2, User as UserIcon, Bell, LogOut, ChevronDown, CheckCircle2, AlertCircle, Sparkles, Calendar, Home, BellRing, Paperclip } from 'lucide-react';
import { Button } from './components/ui/Button';
import { Dropdown, DropdownItem } from './components/ui/Dropdown';
import { Dialog, DialogHeader, DialogTitle, DialogClose } from './components/ui/Dialog';
import { Badge } from './components/ui/Badge';

export default function Chat({ user, onLogout }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null); // Kept state for backend, removed UI

  // Complaint state
  const [complaintPending, setComplaintPending] = useState(null);
  const [complaintSubmitting, setComplaintSubmitting] = useState(false);
  const [complaintResult, setComplaintResult] = useState(null);
  const [votedComplaints, setVotedComplaints] = useState(new Set());

  // Hostel + room location state
  const [hostels, setHostels] = useState([]);
  const [selectedHostelId, setSelectedHostelId] = useState('');
  const [roomNumber, setRoomNumber] = useState('');

  // My Complaints panel
  const [showMyComplaints, setShowMyComplaints] = useState(false);
  const [myComplaints, setMyComplaints] = useState([]);
  const [myComplaintsLoading, setMyComplaintsLoading] = useState(false);

  // Chat History State
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);

  // Notification Center State
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifFilter, setNotifFilter] = useState('all');
  const [notifications, setNotifications] = useState([]);
  const notifPollRef = useRef(null);

  const fetchNotifications = async () => {
    if (!user?.id) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/notifications?user_id=${user.id}`);
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.map(n => ({
          id:      n.id,
          title:   n.notification_title,
          message: n.notification_message,
          time:    formatNotifTime(n.created_at),
          unread:  !n.is_read,
          icon:    n.icon || '📢',
        })));
      }
    } catch (e) {
      console.error('Failed to fetch notifications', e);
    }
  };

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/hostels')
      .then(r => r.ok ? r.json() : [])
      .then(data => setHostels(data))
      .catch(() => {});
  }, []);

  const formatNotifTime = (iso) => {
    if (!iso) return '';
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'Just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  useEffect(() => {
    fetchNotifications();
    notifPollRef.current = setInterval(fetchNotifications, 30000);
    return () => clearInterval(notifPollRef.current);
  }, [user?.id]);

  const notifRef = useRef(null);
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    if (showNotifications) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showNotifications]);

  const unreadCount = notifications.filter(n => n.unread).length;
  const filteredNotifs = notifFilter === 'all' ? notifications : notifications.filter(n => n.unread);

  const markAllRead = async () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
    try {
      await fetch(`http://127.0.0.1:8000/api/notifications/read-all?user_id=${user.id}`, { method: 'PATCH' });
    } catch (e) {
      console.error('Failed to mark all read', e);
    }
  };

  const toggleRead = async (id) => {
    const notif = notifications.find(n => n.id === id);
    if (!notif) return;
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, unread: !n.unread } : n));
    if (notif.unread) {
      try {
        await fetch(`http://127.0.0.1:8000/api/notifications/${id}/read`, { method: 'PATCH' });
      } catch (e) {}
    }
  };

  const deleteNotif = (e, id) => {
    e.stopPropagation();
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  const messagesEndRef = useRef(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages, complaintPending, complaintResult]);

  useEffect(() => {
    fetchChats();
  }, [user.id]);

  const fetchChats = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chats?user_id=${user.id}`);
      if (response.ok) {
        const data = await response.json();
        setChatSessions(data);
      }
    } catch (e) {
      console.error('Failed to fetch chats', e);
    }
  };

  const fetchMyComplaints = async () => {
    if (!user?.id) return;
    setMyComplaintsLoading(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/my-complaints?user_id=${user.id}`);
      if (res.ok) setMyComplaints(await res.json());
    } catch (e) {
      console.error('Failed to fetch my complaints', e);
    } finally {
      setMyComplaintsLoading(false);
    }
  };

  const loadChat = async (chatId) => {
    setActiveChatId(chatId);
    setMessages([]);
    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/chats/${chatId}/messages`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      }
    } catch (e) {
      console.error('Failed to load chat messages', e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setActiveChatId(null);
    setMessages([]);
  };

  const handleDeleteChat = async (e, chatId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/chats/${chatId}`, { method: 'DELETE' });
      if (res.ok) {
        setChatSessions((prev) => prev.filter((c) => c.id !== chatId));
        if (activeChatId === chatId) {
          handleNewChat();
        }
      }
    } catch (err) {
      console.error("Failed to delete chat", err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const inputText = input; 
    const userMessage = { role: 'user', content: inputText };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    
    setComplaintPending(null);
    setComplaintResult(null);
    setSelectedHostelId('');
    setRoomNumber('');

    const metadata_filter = selectedSource ? { source: selectedSource } : null;
    setSelectedSource(null); // Reset after submitting

    if (user?.id) {
      fetch('http://127.0.0.1:8000/api/complaint/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: inputText, user_info: user }),
      })
        .then(r => r.ok ? r.json() : null)
        .then(data => {
          if (data?.is_complaint && data.confidence >= 0.6) {
            setComplaintPending({
              text:      inputText,
              category:  data.category  || 'general',
              title:     data.title     || inputText.slice(0, 60),
              needsRoom: data.needs_room === true,
            });
          }
        })
        .catch(() => {});
    }

    try {
      const payload = {
        query: inputText,
        metadata_filter,
        user_info: user,
      };
      if (activeChatId) {
        payload.chat_id = activeChatId;
      }

      const response = await fetch('http://127.0.0.1:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();
      const botMessage = {
        role: 'bot',
        content: data.answer,
        context: data.context,
        metadata: data.metadata,
      };

      setMessages((prev) => [...prev, botMessage]);

      if (!activeChatId && data.chat_id) {
        setActiveChatId(data.chat_id);
        fetchChats();
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        role: 'bot',
        content: 'Sorry, I encountered an error. Please try again later. Is the backend running?',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitComplaint = async () => {
    if (!complaintPending || complaintSubmitting) return;
    if (!selectedHostelId) {
      alert('Please select your hostel before submitting.');
      return;
    }
    if (complaintPending.needsRoom && !roomNumber.trim()) {
      alert('Please enter your room number.');
      return;
    }
    setComplaintSubmitting(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/complaint', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: complaintPending.text,
          user_info: user,
          hostel_id: selectedHostelId,
          room_number: complaintPending.needsRoom && roomNumber.trim() ? roomNumber.trim() : null,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Submission failed');
      setComplaintResult(data);
      setComplaintPending(null);
      fetchMyComplaints();
    } catch (err) {
      setComplaintResult({ error: err.message });
      setComplaintPending(null);
    } finally {
      setComplaintSubmitting(false);
    }
  };

  const handleVote = async (complaintId) => {
    if (votedComplaints.has(complaintId)) return;
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/complaint/${complaintId}/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: '', user_info: user }),
      });
      if (res.ok) {
        setVotedComplaints(prev => new Set([...prev, complaintId]));
        setComplaintResult(prev => prev ? ({
          ...prev,
          similar: (prev.similar || []).map(s =>
            s.id === complaintId ? { ...s, vote_count: s.vote_count + 1 } : s
          ),
        }) : prev);
      }
    } catch (err) {
      console.error('Vote error:', err);
    }
  };

  return (
    <div className="app-chat-layout">
      {/* ── My Complaints Modal ── */}
      <Dialog open={showMyComplaints} onOpenChange={setShowMyComplaints}>
        <DialogHeader style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
          <DialogTitle>My Complaints</DialogTitle>
          <DialogClose onClick={() => setShowMyComplaints(false)} />
        </DialogHeader>
        <div style={{padding: 'var(--space-4)', maxHeight: '60vh', overflowY: 'auto'}}>
          {myComplaintsLoading ? (
            <div style={{textAlign: 'center', padding: 'var(--space-4)', color: 'var(--cm-muted)'}}>Loading complaints...</div>
          ) : myComplaints.length === 0 ? (
            <div style={{textAlign: 'center', padding: 'var(--space-4)', color: 'var(--cm-muted)'}}>You have not submitted any complaints yet.</div>
          ) : (
            <div style={{display: 'flex', flexDirection: 'column', gap: 'var(--space-3)'}}>
              {myComplaints.map(c => (
                <div key={c.id} style={{backgroundColor: 'var(--cm-secondary)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', border: '1px solid var(--cm-border)'}}>
                  <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-2)'}}>
                    <span style={{fontWeight: 'var(--font-semibold)', fontSize: 'var(--text-sm)'}}>{c.title}</span>
                    <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                      {c.status === 'open' ? 'Open' : c.status === 'in_progress' ? 'In Progress' : c.status === 'resolved' ? 'Resolved' : 'Dismissed'}
                    </Badge>
                  </div>
                  <div style={{fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', marginBottom: 'var(--space-2)'}}>
                    <span style={{textTransform: 'capitalize'}}>{c.category}</span> • {new Date(c.created_at).toLocaleDateString()}
                  </div>
                  <div style={{fontSize: 'var(--text-sm)'}}>{c.description}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Dialog>
      {/* ── Sidebar ── */}
      <div className="chat-sidebar">
        <button className="new-chat-btn" onClick={handleNewChat}>
          <Plus className="cm-icon-sm" style={{marginRight: '8px'}} /> New Chat
        </button>

        <div className="chat-history-container">
          <div style={{fontSize: 'var(--text-xs)', fontWeight: 'var(--font-semibold)', color: 'var(--cm-muted)', padding: 'var(--space-2) var(--space-3)', textTransform: 'uppercase'}}>
            Recent
          </div>
          {chatSessions.map((chat) => (
            <div 
              key={chat.id} 
              className={`chat-history-item ${activeChatId === chat.id ? 'active' : ''}`}
              onClick={() => loadChat(chat.id)}
            >
              <div style={{display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flex: 1, overflow: 'hidden'}}>
                <MessageSquare className="cm-icon-sm" style={{flexShrink: 0}} />
                <span className="chat-history-text">{chat.title}</span>
              </div>
              <button
                type="button"
                className="chat-delete-btn"
                onClick={(e) => handleDeleteChat(e, chat.id)}
              >
                <Trash2 className="cm-icon-sm" />
              </button>
            </div>
          ))}
        </div>

        <div className="sidebar-bottom-container">
          <div className="sidebar-profile-row">
            <div className="user-profile-header">
              <div style={{display: 'flex', alignItems: 'center', gap: 'var(--space-2)'}}>
                <div className="user-avatar-circle">
                  {user?.name ? user.name.charAt(0) : '?'}
                </div>
                <div style={{fontSize: 'var(--text-sm)', fontWeight: 'var(--font-medium)', whiteSpace: 'nowrap'}}>{user?.name || 'User'}</div>
              </div>
              <ChevronDown className="cm-icon-sm text-[var(--cm-muted)]" />
            </div>

          <div style={{position: 'relative'}} ref={notifRef}>
            <button 
              className="chat-delete-btn" 
              style={{padding: 'var(--space-2)', position: 'relative', opacity: 1}}
              onClick={() => setShowNotifications(!showNotifications)}
            >
              <Bell className="cm-icon-md text-[var(--cm-fg)]" />
              {unreadCount > 0 && (
                <span style={{position: 'absolute', top: 0, right: 0, width: '10px', height: '10px', backgroundColor: 'var(--cm-error)', borderRadius: 'var(--radius-full)', border: '2px solid var(--cm-bg)'}}></span>
              )}
            </button>
            
            {showNotifications && (
              <div className="cm-dropdown-content" style={{position: 'absolute', bottom: 'calc(100% + 10px)', left: '-20px', width: '300px', padding: 0, backgroundColor: 'var(--cm-bg)', border: '1px solid var(--cm-border)', borderRadius: 'var(--radius-lg)'}}>
                <div style={{padding: 'var(--space-3)', borderBottom: '1px solid var(--cm-border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                  <span style={{fontWeight: 'var(--font-semibold)'}}>Notifications</span>
                  {unreadCount > 0 && (
                    <button onClick={markAllRead} style={{background: 'transparent', border: 'none', color: 'var(--cm-accent)', fontSize: 'var(--text-xs)', cursor: 'pointer'}}>Mark all read</button>
                  )}
                </div>
                <div style={{maxHeight: '300px', overflowY: 'auto'}}>
                  {filteredNotifs.length === 0 ? (
                    <div style={{padding: 'var(--space-4)', textAlign: 'center', color: 'var(--cm-muted)', fontSize: 'var(--text-sm)'}}>No new notifications</div>
                  ) : (
                    filteredNotifs.map(n => (
                      <div key={n.id} style={{padding: 'var(--space-3)', borderBottom: '1px solid var(--cm-border)', cursor: 'pointer', backgroundColor: n.unread ? 'var(--cm-secondary)' : 'transparent'}} onClick={() => toggleRead(n.id)}>
                        <div style={{display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-1)'}}>
                          <span style={{fontWeight: 'var(--font-medium)', fontSize: 'var(--text-sm)'}}>{n.title}</span>
                          <span style={{fontSize: 'var(--text-xs)', color: 'var(--cm-muted)'}}>{n.time}</span>
                        </div>
                        <div style={{fontSize: 'var(--text-xs)', color: 'var(--cm-muted)'}}>{n.message}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="sidebar-static-menu">
            <button className="sidebar-menu-item" onClick={() => { setShowMyComplaints(true); fetchMyComplaints(); }}>
              <div style={{display: 'flex', alignItems: 'center'}}><AlertCircle className="cm-icon-sm mr-2" /> My Complaints</div>
              <ChevronDown className="cm-icon-sm text-[var(--cm-muted)]" style={{transform: 'rotate(-90deg)'}} />
            </button>
            <button className="sidebar-menu-item" style={{color: 'var(--cm-error)'}} onClick={onLogout}>
              <div style={{display: 'flex', alignItems: 'center'}}><LogOut className="cm-icon-sm mr-2" /> Log out</div>
            </button>
          </div>
        </div>
      </div>

      {/* ── Main Chat Area ── */}
      <div className="chat-main">
        <div className="chat-header-bar">
          <div>
            <div className="chat-header-title">CampusMind</div>
            <div className="chat-header-subtitle">AI Campus Assistant — Academics, notices, and hostel services</div>
          </div>
        </div>

        <div className="chat-messages-scroll">
          <div className="chat-messages-inner">
            {messages.length === 0 && !isLoading && (
              <div className="chat-empty-state">
                <div className="chat-empty-logo">
                  <span style={{fontSize: '28px', fontWeight: '800', letterSpacing: '-0.05em', color: '#60a5fa'}}>CM</span>
                  <Sparkles size={14} style={{position: 'absolute', top: 12, right: 12, color: '#93c5fd'}}/>
                </div>
                <div className="chat-empty-title">How can I help you today?</div>
                <div className="chat-empty-desc">
                  Ask me about your syllabus, important campus notices, hostel issues, or anything related to <span style={{color: '#60a5fa'}}>NIT Silchar</span>.
                </div>
              </div>
            )}

            {messages.map((msg, idx) => (
              <div key={idx} className={`chat-bubble-row ${msg.role}`}>
                <div className={`chat-bubble ${msg.role}`}>
                  <p style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</p>
                </div>
              </div>
            ))}
            
            {isLoading && (
              <div className="chat-bubble-row bot">
                <div className="chat-bubble bot" style={{display: 'flex', alignItems: 'center', gap: 'var(--space-2)', color: 'var(--cm-muted)'}}>
                  <Loader2 className="animate-spin cm-icon-sm" /> Thinking...
                </div>
              </div>
            )}

            {/* ── Complaint Banner ── */}
            {complaintPending && !complaintResult && (
              <div className="chat-complaint-banner">
                <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-4)'}}>
                  <div style={{display: 'flex', gap: 'var(--space-3)'}}>
                    <AlertCircle className="cm-icon-lg text-amber-500" />
                    <div>
                      <div style={{fontWeight: 'var(--font-semibold)', color: 'var(--cm-fg)'}}>File a formal complaint?</div>
                      <div style={{fontSize: 'var(--text-sm)', color: 'var(--cm-muted)'}}>We detected an issue regarding: <strong style={{color: 'var(--cm-fg)'}}>{complaintPending.category}</strong></div>
                    </div>
                  </div>
                  <button onClick={() => setComplaintPending(null)} style={{background: 'transparent', border: 'none', color: 'var(--cm-muted)', cursor: 'pointer'}}>✕</button>
                </div>

                <div style={{display: 'flex', flexWrap: 'wrap', gap: 'var(--space-4)', marginBottom: 'var(--space-4)'}}>
                  <div style={{flex: '1 1 200px'}}>
                    <label style={{display: 'block', fontSize: 'var(--text-xs)', fontWeight: 'var(--font-medium)', marginBottom: 'var(--space-1)', color: 'var(--cm-muted)'}}>Hostel</label>
                    <select
                      style={{width: '100%', padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', outline: 'none'}}
                      value={selectedHostelId}
                      onChange={e => setSelectedHostelId(e.target.value)}
                    >
                      <option value="">Select hostel…</option>
                      {hostels.map(h => (
                        <option key={h.id} value={h.id}>{h.code} – {h.name}</option>
                      ))}
                    </select>
                  </div>
                  
                  {complaintPending.needsRoom && (
                    <div style={{flex: '1 1 200px'}}>
                      <label style={{display: 'block', fontSize: 'var(--text-xs)', fontWeight: 'var(--font-medium)', marginBottom: 'var(--space-1)', color: 'var(--cm-muted)'}}>Room Number</label>
                      <input
                        style={{width: '100%', padding: 'var(--space-2)', borderRadius: 'var(--radius-md)', background: 'var(--cm-bg)', color: 'var(--cm-fg)', border: '1px solid var(--cm-border)', outline: 'none'}}
                        type="text"
                        placeholder="e.g. 204"
                        value={roomNumber}
                        onChange={e => setRoomNumber(e.target.value)}
                        maxLength={10}
                      />
                    </div>
                  )}
                </div>

                <div style={{display: 'flex', gap: 'var(--space-3)'}}>
                  <Button onClick={handleSubmitComplaint} disabled={complaintSubmitting || !selectedHostelId || (complaintPending.needsRoom && !roomNumber.trim())} isLoading={complaintSubmitting}>
                    Submit Complaint
                  </Button>
                  <Button variant="ghost" onClick={() => setComplaintPending(null)}>
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {complaintResult && !complaintResult.error && (
              <div className="chat-complaint-banner" style={{background: 'rgba(16, 185, 129, 0.1)', borderColor: 'rgba(16, 185, 129, 0.2)'}}>
                <div style={{display: 'flex', gap: 'var(--space-3)', alignItems: 'center'}}>
                  <CheckCircle2 className="cm-icon-lg text-emerald-500" />
                  <div>
                    <div style={{fontWeight: 'var(--font-semibold)', color: 'var(--cm-fg)'}}>Complaint Submitted successfully!</div>
                    <div style={{fontSize: 'var(--text-sm)', color: 'var(--cm-muted)'}}>{complaintResult.title}</div>
                  </div>
                </div>
              </div>
            )}

            {complaintResult?.error && (
              <div className="chat-complaint-banner" style={{background: 'rgba(239, 68, 68, 0.1)', borderColor: 'rgba(239, 68, 68, 0.2)'}}>
                <div style={{fontWeight: 'var(--font-semibold)', color: 'var(--cm-error)'}}>Submission Failed</div>
                <div style={{fontSize: 'var(--text-sm)', color: 'var(--cm-muted)'}}>{complaintResult.error}</div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        <div className="chat-input-container">
          {messages.length === 0 && !isLoading && (
            <div className="quick-actions-grid">
              <button className="qa-card" type="button" onClick={() => { setInput('Show me the academic calendar'); setSelectedSource('academic'); }}>
                <Calendar className="qa-icon" />
                <div className="qa-text">Academic Calendar</div>
              </button>
              <button className="qa-card" type="button" onClick={() => { setInput('I want to report an issue with my hostel'); setSelectedSource('hostel'); }}>
                <Home className="qa-icon" />
                <div className="qa-text">Hostel Information</div>
              </button>
              <button className="qa-card" type="button" onClick={() => { setInput('Are there any new notices?'); setSelectedSource('notices'); }}>
                <BellRing className="qa-icon" />
                <div className="qa-text">Notices &<br/>Announcements</div>
              </button>
              <button className="qa-card" type="button" onClick={() => { setInput('I want to report an issue'); setSelectedSource('hostel'); }}>
                <AlertCircle className="qa-icon" />
                <div className="qa-text">Report an<br/>Issue</div>
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
            <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
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
          <div style={{textAlign: 'center', marginTop: '16px', fontSize: '0.7rem', color: '#94a3b8', display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '4px'}}>
            <CheckCircle2 size={12} /> CampusMind can make mistakes. Consider verifying important information.
          </div>
        </div>
      </div>
    </div>
  );
}
