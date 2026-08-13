/**
 * src/pages/AdminPage.jsx — Container Page for Admin Dashboard
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Shield, ArrowLeft, Megaphone, AlertCircle, Database } from 'lucide-react';
import { Button } from '../components/ui/Button';
import DocumentIngestion from '../components/admin/DocumentIngestion';
import NoticeBroadcast from '../components/admin/NoticeBroadcast';
import ComplaintManagement from '../components/admin/ComplaintManagement';
import { useAdminComplaints } from '../hooks/useAdminComplaints';
import { uploadDocumentApi, getDocumentsApi, deleteDocumentApi, postNoticeApi, getNoticesListApi } from '../api/notices';

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

export default function AdminPage({ onBack }) {
  const [activeTab, setActiveTab] = useState('upload');

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

  // ── Complaints (via hook) ──
  const {
    complaints,
    isLoadingComplaints,
    complaintStatusFilter,
    setComplaintStatusFilter,
    complaintCategoryFilter,
    setComplaintCategoryFilter,
    updatingComplaintId,
    fetchComplaints,
    updateComplaintStatus,
  } = useAdminComplaints();

  // ── Fetch functions ──
  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const data = await getDocumentsApi();
      setDocuments(data || []);
    } catch (e) {
      console.error('Failed to load documents', e);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  const fetchPostedNotices = useCallback(async () => {
    setIsLoadingNotices(true);
    try {
      const data = await getNoticesListApi();
      setPostedNotices(data || []);
    } catch (e) {
      console.error('Failed to load notices', e);
    } finally {
      setIsLoadingNotices(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadAdminData = async () => {
      if (isMounted) {
        await fetchDocuments();
        await fetchPostedNotices();
        await fetchComplaints();
      }
    };
    loadAdminData();
    return () => { isMounted = false; };
  }, [fetchDocuments, fetchPostedNotices, fetchComplaints]);

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

    try {
      const t1 = setTimeout(() => setUploadStep('Detecting content type...'), 1000);
      const t2 = setTimeout(() => setUploadStep('Extracting & chunking...'), 2500);
      const t3 = setTimeout(() => setUploadStep('Generating embeddings...'), 5000);
      const t4 = setTimeout(() => setUploadStep('Indexing into pgvector...'), 9000);
      const t5 = setTimeout(() => setUploadStep('Running agentic classifier...'), 13000);

      const data = await uploadDocumentApi(selectedFile);
      [t1, t2, t3, t4, t5].forEach(clearTimeout);

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
      await deleteDocumentApi(filename);
      setUploadAlert({ type: 'success', text: `Removed '${filename}' from database.` });
      fetchDocuments();
    } catch (err) {
      setUploadAlert({ type: 'error', text: err.message });
    }
  };

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
      const data = await postNoticeApi(noticeTitle, noticeContent);
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
          {activeTab === 'upload' && (
            <DocumentIngestion
              documents={documents}
              isLoadingDocs={isLoadingDocs}
              selectedFile={selectedFile}
              fileInputRef={fileInputRef}
              handleFileSelect={handleFileSelect}
              handleDrop={handleDrop}
              handleUpload={handleUpload}
              isUploading={isUploading}
              uploadStep={uploadStep}
              uploadAlert={uploadAlert}
              agentResult={agentResult}
              handleDelete={handleDelete}
              fetchDocuments={fetchDocuments}
            />
          )}

          {activeTab === 'notice' && (
            <NoticeBroadcast
              noticeTitle={noticeTitle}
              setNoticeTitle={setNoticeTitle}
              noticeContent={noticeContent}
              setNoticeContent={setNoticeContent}
              isPostingNotice={isPostingNotice}
              noticeAlert={noticeAlert}
              noticeResult={noticeResult}
              handlePostNotice={handlePostNotice}
              postedNotices={postedNotices}
              isLoadingNotices={isLoadingNotices}
              fetchPostedNotices={fetchPostedNotices}
              formatDate={formatDate}
              NOTICE_TYPE_LABELS={NOTICE_TYPE_LABELS}
            />
          )}

          {activeTab === 'complaints' && (
            <ComplaintManagement
              complaints={complaints}
              isLoadingComplaints={isLoadingComplaints}
              complaintStatusFilter={complaintStatusFilter}
              setComplaintStatusFilter={setComplaintStatusFilter}
              complaintCategoryFilter={complaintCategoryFilter}
              setComplaintCategoryFilter={setComplaintCategoryFilter}
              fetchComplaints={fetchComplaints}
              updateComplaintStatus={updateComplaintStatus}
              updatingComplaintId={updatingComplaintId}
              formatDate={formatDate}
            />
          )}
        </div>
      </div>
    </div>
  );
}
