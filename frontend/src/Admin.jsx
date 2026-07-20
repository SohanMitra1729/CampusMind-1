import React, { useState, useEffect, useRef } from 'react';
import { Shield, ArrowLeft, Upload, FileText, Trash2, Megaphone, CheckCircle2, AlertCircle, RefreshCw, Users, Database, User as UserIcon } from 'lucide-react';
import { Button } from './components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from './components/ui/Card';
import { Badge } from './components/ui/Badge';
import { Input } from './components/ui/Input';
import { Textarea } from './components/ui/Textarea';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const NOTICE_TYPE_LABELS = {
  holiday:        { label: 'Holiday',        icon: '🏖️', color: 'emerald' },
  exam_notice:    { label: 'Exam Notice',    icon: '📝', color: 'amber' },
  fee_notice:     { label: 'Fee Notice',     icon: '💰', color: 'red' },
  student_notice: { label: 'Student Notice', icon: '📢', color: 'indigo' },
  scholarship:    { label: 'Scholarship',    icon: '🎓', color: 'violet' },
  internship:     { label: 'Internship',     icon: '💼', color: 'sky' },
  event_notice:   { label: 'Event',          icon: '📅', color: 'pink' },
  general:        { label: 'General',        icon: '📄', color: 'slate' },
};

export default function Admin({ onBack }) {
  const [activeTab, setActiveTab] = useState('upload'); // 'upload' | 'notice' | 'complaints'

  // ── Upload PDF state ──
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState('');
  const [uploadAlert, setUploadAlert] = useState(null);
  const [agentResult, setAgentResult] = useState(null);
  const fileInputRef = useRef(null);

  // ── Post Notice state ──
  const [noticeTitle, setNoticeTitle] = useState('');
  const [noticeContent, setNoticeContent] = useState('');
  const [isPostingNotice, setIsPostingNotice] = useState(false);
  const [noticeAlert, setNoticeAlert] = useState(null);
  const [noticeResult, setNoticeResult] = useState(null);
  const [postedNotices, setPostedNotices] = useState([]);
  const [isLoadingNotices, setIsLoadingNotices] = useState(false);

  // ── Complaints state ──
  const [complaints, setComplaints] = useState([]);
  const [isLoadingComplaints, setIsLoadingComplaints] = useState(false);
  const [complaintStatusFilter, setComplaintStatusFilter] = useState('');
  const [complaintCategoryFilter, setComplaintCategoryFilter] = useState('');
  const [updatingComplaintId, setUpdatingComplaintId] = useState(null);

  useEffect(() => {
    fetchDocuments();
    fetchPostedNotices();
    fetchComplaints();
  }, []);

  // ── Fetch functions ──
  const fetchDocuments = async () => {
    setIsLoadingDocs(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/documents`);
      if (res.ok) setDocuments(await res.json());
    } catch (e) {
      console.error('Failed to load documents', e);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const fetchPostedNotices = async () => {
    setIsLoadingNotices(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/notices-list`);
      if (res.ok) setPostedNotices(await res.json());
    } catch (e) {
      console.error('Failed to load notices', e);
    } finally {
      setIsLoadingNotices(false);
    }
  };

  const fetchComplaints = async (status = '', category = '') => {
    setIsLoadingComplaints(true);
    try {
      const params = new URLSearchParams();
      if (status)   params.append('status',   status);
      if (category) params.append('category', category);
      const res = await fetch(`${API_BASE_URL}/api/admin/complaints?${params}`);
      if (res.ok) setComplaints(await res.json());
    } catch (e) {
      console.error('Failed to load complaints', e);
    } finally {
      setIsLoadingComplaints(false);
    }
  };

  const updateComplaintStatus = async (complaintId, newStatus) => {
    setUpdatingComplaintId(complaintId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/complaints/${complaintId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        // Optimistically update and filter out if it no longer matches the current tab
        setComplaints(prev => prev.map(c => 
          c.id === complaintId ? { ...c, status: newStatus } : c
        ).filter(c => {
          // If we are on a specific status tab, remove it if it no longer matches
          if (complaintStatusFilter && complaintStatusFilter !== newStatus) {
            return false;
          }
          return true;
        }));
      }
    } catch (e) {
      console.error('Failed to update status', e);
    } finally {
      setUpdatingComplaintId(null);
    }
  };

  // ── Upload handlers ──
  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadAlert({ type: 'error', text: 'Please select a valid PDF document.' });
        return;
      }
      setSelectedFile(file);
      setUploadAlert(null);
      setAgentResult(null);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        setUploadAlert({ type: 'error', text: 'Only PDF documents are accepted.' });
        return;
      }
      setSelectedFile(file);
      setUploadAlert(null);
      setAgentResult(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;
    setIsUploading(true);
    setUploadAlert(null);
    setAgentResult(null);
    setUploadStep('Uploading file to server...');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const t1 = setTimeout(() => setUploadStep('Detecting content type...'), 1000);
      const t2 = setTimeout(() => setUploadStep('Extracting & chunking...'), 2500);
      const t3 = setTimeout(() => setUploadStep('Generating embeddings...'), 5000);
      const t4 = setTimeout(() => setUploadStep('Indexing into pgvector...'), 9000);
      const t5 = setTimeout(() => setUploadStep('Running agentic classifier...'), 13000);

      const res = await fetch(`${API_BASE_URL}/api/admin/upload`, {
        method: 'POST',
        body: formData,
      });

      [t1, t2, t3, t4, t5].forEach(clearTimeout);

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      const typeLabel = data.content_type_detected === 'tabular' ? 'Tabular' : 'Text';

      setUploadAlert({
        type: 'success',
        text: `Ingested '${selectedFile.name}' (${typeLabel}) — ${data.chunks_created} chunks indexed.`,
      });

      if (data.agent) {
        setAgentResult(data.agent);
      }

      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchDocuments();
      fetchPostedNotices();
    } catch (err) {
      setUploadAlert({ type: 'error', text: err.message });
    } finally {
      setIsUploading(false);
      setUploadStep('');
    }
  };

  const handleDelete = async (filename) => {
    if (!window.confirm(`Remove '${filename}' from the knowledge base?`)) return;
    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/documents/${encodeURIComponent(filename)}`, {
        method: 'DELETE',
      });
      if (res.ok) {
        setUploadAlert({ type: 'success', text: `Removed '${filename}' from database.` });
        fetchDocuments();
      } else {
        throw new Error('Failed to delete document');
      }
    } catch (err) {
      setUploadAlert({ type: 'error', text: err.message });
    }
  };

  // ── Notice handlers ──
  const handlePostNotice = async (e) => {
    e.preventDefault();
    if (!noticeTitle.trim() || !noticeContent.trim()) {
      setNoticeAlert({ type: 'error', text: 'Both title and content are required.' });
      return;
    }
    setIsPostingNotice(true);
    setNoticeAlert(null);
    setNoticeResult(null);

    try {
      const res = await fetch(`${API_BASE_URL}/api/admin/notices`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: noticeTitle, content: noticeContent }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to post notice');
      }

      const data = await res.json();
      setNoticeResult(data);
      setNoticeAlert({ type: 'success', text: 'Notice posted successfully!' });
      setNoticeTitle('');
      setNoticeContent('');
      fetchPostedNotices();
    } catch (err) {
      setNoticeAlert({ type: 'error', text: err.message });
    } finally {
      setIsPostingNotice(false);
    }
  };

  const formatDate = (iso) => {
    if (!iso) return '';
    return new Date(iso).toLocaleString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  };

  return (
    <div className="admin-layout">
      <header className="admin-navbar">
        <div className="admin-brand">
          <div className="admin-brand-icon">
            <Shield className="cm-icon-sm" />
          </div>
          <div className="admin-brand-text">
            <h1>Admin Portal</h1>
            <p>Knowledge Base & Communications</p>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="cm-icon-sm mr-2" /> Back to App
        </Button>
      </header>

      <div className="admin-main">
        <div className="admin-header-section">
          <h2 className="admin-header-title">Dashboard</h2>
          <div className="admin-tabs-list">
            <button className={`admin-tab-item ${activeTab === 'upload' ? 'active' : ''}`} onClick={() => setActiveTab('upload')}>
              <Database className="cm-icon-sm" /> Knowledge Base
            </button>
            <button className={`admin-tab-item ${activeTab === 'notice' ? 'active' : ''}`} onClick={() => setActiveTab('notice')}>
              <Megaphone className="cm-icon-sm" /> Broadcasts
            </button>
            <button className={`admin-tab-item ${activeTab === 'complaints' ? 'active' : ''}`} onClick={() => { setActiveTab('complaints'); fetchComplaints(complaintStatusFilter, complaintCategoryFilter); }}>
              <AlertCircle className="cm-icon-sm" /> Complaints
              {complaints.filter(c => c.status === 'open').length > 0 && (
                <span className="admin-tab-badge">{complaints.filter(c => c.status === 'open').length}</span>
              )}
            </button>
          </div>
        </div>

        <div className="admin-content-container">
          
          {/* ── Tab: Upload PDF ── */}
          {activeTab === 'upload' && (
            <div className="admin-grid">
              {/* Upload Card */}
              <Card>
                <CardHeader>
                  <CardTitle>Ingest New Document</CardTitle>
                  <CardDescription>Upload PDFs to automatically index them into the RAG system and notify relevant students.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {uploadAlert && (
                    <div className={`p-3 rounded-md text-sm flex items-start gap-2 ${uploadAlert.type === 'error' ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'}`}>
                      {uploadAlert.type === 'error' ? <AlertCircle className="cm-icon-sm shrink-0 mt-0.5" /> : <CheckCircle2 className="cm-icon-sm shrink-0 mt-0.5" />}
                      {uploadAlert.text}
                    </div>
                  )}

                  {agentResult && (
                    <div className="bg-[var(--cm-secondary)] rounded-lg p-4 border border-[var(--cm-border)] space-y-3">
                      <div className="text-sm font-semibold flex items-center gap-2"><CheckCircle2 className="cm-icon-sm text-emerald-500" /> Agent Pipeline Result</div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-[var(--cm-muted)] text-xs uppercase tracking-wider block mb-1">Type</span>
                          <span>{NOTICE_TYPE_LABELS[agentResult.doc_type]?.icon} {NOTICE_TYPE_LABELS[agentResult.doc_type]?.label || agentResult.doc_type}</span>
                        </div>
                        <div>
                          <span className="text-[var(--cm-muted)] text-xs uppercase tracking-wider block mb-1">Notifications</span>
                          <span>{agentResult.notification_skipped ? 'Skipped' : `${agentResult.notifications_sent} Sent`}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div
                    className={`admin-dropzone ${selectedFile ? 'has-file' : ''}`}
                    onDrop={handleDrop}
                    onDragOver={(e) => e.preventDefault()}
                    onClick={() => !isUploading && fileInputRef.current?.click()}
                  >
                    <input type="file" ref={fileInputRef} onChange={handleFileSelect} accept=".pdf" style={{ display: 'none' }} disabled={isUploading} />
                    {selectedFile ? (
                      <div className="flex flex-col items-center gap-2">
                        <FileText className="cm-icon-lg text-[var(--cm-primary)]" />
                        <span className="font-medium text-[var(--cm-fg)]">{selectedFile.name}</span>
                        <span className="text-sm text-[var(--cm-muted)]">{(selectedFile.size / (1024 * 1024)).toFixed(2)} MB</span>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-2 text-[var(--cm-muted)]">
                        <Upload className="cm-icon-lg mb-2" />
                        <span className="font-medium text-[var(--cm-fg)]">Drag & drop PDF here</span>
                        <span className="text-sm">or click to browse</span>
                      </div>
                    )}
                  </div>

                  {selectedFile && !isUploading && (
                    <div className="flex gap-3">
                      <Button className="w-full" onClick={handleUpload}>Start Ingestion</Button>
                      <Button variant="ghost" onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}>Cancel</Button>
                    </div>
                  )}

                  {isUploading && (
                    <div className="flex items-center gap-3 p-4 bg-[var(--cm-secondary)] rounded-lg text-sm">
                      <RefreshCw className="cm-icon-sm animate-spin text-[var(--cm-primary)]" />
                      <span>{uploadStep}</span>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Repository Table */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Knowledge Base</CardTitle>
                    <CardDescription>Indexed documents available for RAG</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" onClick={fetchDocuments} disabled={isLoadingDocs}><RefreshCw className={`cm-icon-sm mr-2 ${isLoadingDocs ? 'animate-spin' : ''}`} /> Refresh</Button>
                </CardHeader>
                <CardContent>
                  {isLoadingDocs ? (
                    <div className="py-8 text-center text-[var(--cm-muted)] text-sm">Fetching vector store...</div>
                  ) : documents.length === 0 ? (
                    <div className="py-8 text-center text-[var(--cm-muted)] text-sm">No indexed documents found.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="admin-repo-table">
                        <thead>
                          <tr>
                            <th>Document</th>
                            <th>Chunks</th>
                            <th style={{ textAlign: 'right' }}>Action</th>
                          </tr>
                        </thead>
                        <tbody>
                          {documents.map((doc) => (
                            <tr key={doc.filename}>
                              <td className="font-medium"><FileText className="cm-icon-sm inline mr-2 text-[var(--cm-muted)]" />{doc.filename}</td>
                              <td><Badge variant="secondary">{doc.chunks}</Badge></td>
                              <td style={{ textAlign: 'right' }}>
                                <Button variant="ghost" size="sm" onClick={() => handleDelete(doc.filename)} className="text-red-500 hover:text-red-400 hover:bg-red-500/10">
                                  <Trash2 className="cm-icon-sm" />
                                </Button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* ── Tab: Post Notice ── */}
          {activeTab === 'notice' && (
            <div className="admin-grid">
              {/* Notice Form */}
              <Card>
                <CardHeader>
                  <CardTitle>Broadcast Notice</CardTitle>
                  <CardDescription>Target specific students (via Scholar ID) or broadcast to all.</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {noticeAlert && (
                     <div className={`p-3 rounded-md text-sm flex items-start gap-2 ${noticeAlert.type === 'error' ? 'bg-red-500/10 text-red-500 border border-red-500/20' : 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'}`}>
                      {noticeAlert.type === 'error' ? <AlertCircle className="cm-icon-sm shrink-0 mt-0.5" /> : <CheckCircle2 className="cm-icon-sm shrink-0 mt-0.5" />}
                      {noticeAlert.text}
                    </div>
                  )}
                  
                  {noticeResult && (
                    <div className="bg-[var(--cm-secondary)] rounded-lg p-4 border border-[var(--cm-border)] space-y-3">
                      <div className="text-sm font-semibold flex items-center gap-2"><CheckCircle2 className="cm-icon-sm text-emerald-500" /> Pipeline Completed</div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-[var(--cm-muted)] text-xs uppercase tracking-wider block mb-1">Audience</span>
                          <span>{noticeResult.is_broadcast ? 'All Students' : `${noticeResult.scholar_ids_found.length} Targeted`}</span>
                        </div>
                        <div>
                          <span className="text-[var(--cm-muted)] text-xs uppercase tracking-wider block mb-1">Status</span>
                          <span>{noticeResult.students_notified} Notified</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <form onSubmit={handlePostNotice} className="space-y-4">
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-[var(--cm-muted)] uppercase tracking-wider">Title</label>
                      <Input value={noticeTitle} onChange={e => setNoticeTitle(e.target.value)} placeholder="Notice Title" disabled={isPostingNotice} />
                    </div>
                    <div className="space-y-2">
                      <label className="text-xs font-semibold text-[var(--cm-muted)] uppercase tracking-wider">Content</label>
                      <Textarea value={noticeContent} onChange={e => setNoticeContent(e.target.value)} placeholder="Notice details..." rows={6} disabled={isPostingNotice} />
                    </div>
                    <Button type="submit" className="w-full" isLoading={isPostingNotice}>Dispatch Broadcast</Button>
                  </form>
                </CardContent>
              </Card>

              {/* Posted Notices List */}
              <Card>
                <CardHeader className="flex flex-row items-center justify-between">
                  <div>
                    <CardTitle>Recent Broadcasts</CardTitle>
                    <CardDescription>Log of all dispatched notices</CardDescription>
                  </div>
                  <Button variant="ghost" size="sm" onClick={fetchPostedNotices} disabled={isLoadingNotices}><RefreshCw className={`cm-icon-sm mr-2 ${isLoadingNotices ? 'animate-spin' : ''}`} /> Refresh</Button>
                </CardHeader>
                <CardContent>
                   {isLoadingNotices ? (
                    <div className="py-8 text-center text-[var(--cm-muted)] text-sm">Loading broadcasts...</div>
                  ) : postedNotices.length === 0 ? (
                    <div className="py-8 text-center text-[var(--cm-muted)] text-sm">No broadcasts found.</div>
                  ) : (
                    <div className="space-y-0">
                      {postedNotices.map((notice) => {
                        const typeInfo = NOTICE_TYPE_LABELS[notice.notice_type] || NOTICE_TYPE_LABELS.general;
                        return (
                          <div key={notice.id} className="admin-notice-item">
                            <div className="text-2xl mt-1">{typeInfo.icon}</div>
                            <div className="flex-1">
                              <div className="font-semibold text-sm mb-1">{notice.title}</div>
                              <div className="flex flex-wrap gap-2 text-xs mb-2">
                                <Badge variant="secondary">{typeInfo.label}</Badge>
                                {notice.is_broadcast ? <Badge variant="outline">Broadcast</Badge> : <Badge variant="outline">Targeted</Badge>}
                                <span className="text-[var(--cm-muted)]">{notice.notified_count} notified</span>
                              </div>
                              <div className="text-xs text-[var(--cm-muted)]">{formatDate(notice.created_at)}</div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          )}

          {/* ── Tab: Complaints ── */}
          {activeTab === 'complaints' && (
            <div className="space-y-6">
              <div className="flex items-center gap-4 bg-[var(--cm-secondary)] p-4 rounded-lg border border-[var(--cm-border)]">
                <div className="flex-1 space-y-1">
                  <label className="text-xs font-semibold text-[var(--cm-muted)] uppercase tracking-wider">Status Filter</label>
                  <div className="flex gap-2">
                    {['', 'open', 'in_progress', 'resolved', 'dismissed'].map(s => (
                      <Button key={s} variant={complaintStatusFilter === s ? 'primary' : 'secondary'} size="sm" onClick={() => { setComplaintStatusFilter(s); fetchComplaints(s, complaintCategoryFilter); }}>
                        {s === '' ? 'All' : s === 'in_progress' ? 'In Progress' : s.charAt(0).toUpperCase() + s.slice(1)}
                      </Button>
                    ))}
                  </div>
                </div>
                <div className="flex-1 space-y-1">
                  <label className="text-xs font-semibold text-[var(--cm-muted)] uppercase tracking-wider">Category Filter</label>
                  <select 
                    className="w-full bg-[var(--cm-bg)] border border-[var(--cm-border)] text-[var(--cm-fg)] rounded-md px-3 py-1.5 text-sm outline-none"
                    value={complaintCategoryFilter}
                    onChange={(e) => { setComplaintCategoryFilter(e.target.value); fetchComplaints(complaintStatusFilter, e.target.value); }}
                  >
                    <option value="">All Categories</option>
                    {['hostel', 'academic', 'admin', 'facility', 'mess', 'transport', 'general'].map(c => (
                      <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
                    ))}
                  </select>
                </div>
                <div>
                   <Button variant="ghost" onClick={() => fetchComplaints(complaintStatusFilter, complaintCategoryFilter)} disabled={isLoadingComplaints}>
                    <RefreshCw className={`cm-icon-sm mr-2 ${isLoadingComplaints ? 'animate-spin' : ''}`} /> Refresh
                  </Button>
                </div>
              </div>

              {isLoadingComplaints ? (
                <div className="py-12 text-center text-[var(--cm-muted)]">Loading complaints...</div>
              ) : complaints.length === 0 ? (
                <div className="py-12 text-center text-[var(--cm-muted)] border border-dashed border-[var(--cm-border)] rounded-lg">No complaints match the criteria.</div>
              ) : (
                <div className="admin-complaints-list">
                  {complaints.map(c => (
                    <Card key={c.id} className={`admin-complaint-card ${c.status}`}>
                      <CardContent className="p-6">
                        <div className="admin-complaint-header-row">
                          <div className="flex gap-3">
                            <div className="text-2xl mt-1">{c.category_icon}</div>
                            <div>
                              <div className="font-semibold text-lg mb-1">{c.title}</div>
                              <div className="flex flex-wrap items-center gap-3 text-xs text-[var(--cm-muted)]">
                                <Badge variant={c.status === 'open' ? 'destructive' : c.status === 'in_progress' ? 'warning' : c.status === 'resolved' ? 'success' : 'secondary'}>
                                  {c.status === 'open' ? 'Open' : c.status === 'in_progress' ? 'In Progress' : c.status === 'resolved' ? 'Resolved' : 'Dismissed'}
                                </Badge>
                                <span className="flex items-center gap-1"><UserIcon className="cm-icon-xs" /> {c.student_name} ({c.scholar_id})</span>
                                <span className="flex items-center gap-1"><Users className="cm-icon-xs" /> {c.vote_count} votes</span>
                                <span>{formatDate(c.created_at)}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        <p className="mt-4 text-sm text-[var(--cm-fg)] leading-relaxed">
                          {c.description}
                        </p>

                        {c.hostel_details && Object.keys(c.hostel_details).filter(k => !['raw_chunk','source_doc'].includes(k)).length > 0 && (
                          <div className="mt-4 bg-[var(--cm-bg)] p-3 rounded-md border border-[var(--cm-border)] text-xs">
                            <div className="font-semibold mb-2 flex items-center gap-2">🏠 Enriched Details</div>
                            <div className="grid grid-cols-2 gap-2">
                              {Object.entries(c.hostel_details).filter(([k]) => !['raw_chunk', 'source_doc'].includes(k)).slice(0, 4).map(([k, v]) => (
                                <div key={k}><span className="text-[var(--cm-muted)] capitalize">{k.replace(/_/g, ' ')}:</span> {v}</div>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="admin-complaint-actions">
                          {c.status === 'open' && (
                            <>
                              <Button size="sm" variant="secondary" onClick={() => updateComplaintStatus(c.id, 'in_progress')} isLoading={updatingComplaintId === c.id}>Mark In Progress</Button>
                              <Button size="sm" variant="success" onClick={() => updateComplaintStatus(c.id, 'resolved')} isLoading={updatingComplaintId === c.id}>Resolve</Button>
                              <Button size="sm" variant="ghost" onClick={() => updateComplaintStatus(c.id, 'dismissed')} isLoading={updatingComplaintId === c.id}>Dismiss</Button>
                            </>
                          )}
                          {c.status === 'in_progress' && (
                            <>
                              <Button size="sm" variant="success" onClick={() => updateComplaintStatus(c.id, 'resolved')} isLoading={updatingComplaintId === c.id}>Resolve</Button>
                              <Button size="sm" variant="ghost" onClick={() => updateComplaintStatus(c.id, 'dismissed')} isLoading={updatingComplaintId === c.id}>Dismiss</Button>
                            </>
                          )}
                          {(c.status === 'resolved' || c.status === 'dismissed') && (
                            <Button size="sm" variant="outline" onClick={() => updateComplaintStatus(c.id, 'open')} isLoading={updatingComplaintId === c.id}>Reopen</Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
