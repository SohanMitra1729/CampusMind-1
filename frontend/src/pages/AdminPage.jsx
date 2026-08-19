/**
 * src/pages/AdminPage.jsx — Container Page for Admin Dashboard
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { Shield, ArrowLeft, Megaphone, AlertCircle, Database, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import DocumentIngestion from '../components/admin/DocumentIngestion';
import NoticeBroadcast from '../components/admin/NoticeBroadcast';
import ComplaintManagement from '../components/admin/ComplaintManagement';
import KnowledgeInsights from '../components/admin/KnowledgeInsights';
import { useAdminComplaints } from '../hooks/useAdminComplaints';
import {
  uploadDocumentApi,
  getDocumentsApi,
  deleteDocumentApi,
  postNoticeApi,
  getNoticesListApi,
  deleteNoticeApi,
  getKnowledgeGapsApi,
  approveKnowledgeGapApi,
  dismissKnowledgeGapApi,
} from '../api/notices';

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
  const [docToDelete, setDocToDelete] = useState(null);
  const [isDeletingDoc, setIsDeletingDoc] = useState(false);
  const fileInputRef = useRef(null);

  // ── Post Notice state ──
  const [noticeTitle, setNoticeTitle] = useState('');
  const [noticeContent, setNoticeContent] = useState('');
  const [isPostingNotice, setIsPostingNotice] = useState(false);
  const [noticeAlert, setNoticeAlert] = useState(null);
  const [noticeResult, setNoticeResult] = useState(null);
  const [postedNotices, setPostedNotices] = useState([]);
  const [isLoadingNotices, setIsLoadingNotices] = useState(false);
  const [noticeToDelete, setNoticeToDelete] = useState(null);
  const [isDeletingNotice, setIsDeletingNotice] = useState(false);

  // ── Knowledge Gaps / Insights state ──
  const [gaps, setGaps] = useState([]);
  const [isLoadingGaps, setIsLoadingGaps] = useState(false);

  // ── Complaints (via hook) ──
  const {
    complaints,
    isLoadingComplaints,
    complaintStatusFilter,
    setComplaintStatusFilter,
    complaintCategoryFilter,
    setComplaintCategoryFilter,
    complaintStaffRoleFilter,
    setComplaintStaffRoleFilter,
    complaintScopeFilter,
    setComplaintScopeFilter,
    updatingComplaintId,
    deletingComplaintId,
    fetchComplaints,
    updateComplaintStatus,
    deleteComplaint,
  } = useAdminComplaints();

  // ── Fetch functions ──
  const fetchDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const data = await getDocumentsApi();
      setDocuments(data || []);
    } catch (e) {
      console.error('Failed to load documents', e);
      toast.error('Failed to load knowledge base documents.');
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
      toast.error('Failed to load broadcasts list.');
    } finally {
      setIsLoadingNotices(false);
    }
  }, []);

  const fetchGaps = useCallback(async () => {
    setIsLoadingGaps(true);
    try {
      const data = await getKnowledgeGapsApi();
      setGaps(data || []);
    } catch (e) {
      console.error('Failed to load knowledge gaps', e);
    } finally {
      setIsLoadingGaps(false);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const loadAdminData = async () => {
      if (isMounted) {
        await fetchDocuments();
        await fetchPostedNotices();
        await fetchComplaints();
        await fetchGaps();
      }
    };
    loadAdminData();
    return () => { isMounted = false; };
  }, [fetchDocuments, fetchPostedNotices, fetchComplaints, fetchGaps]);

  const handleFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        const err = 'Please select a valid PDF document.';
        setUploadAlert({ type: 'error', text: err });
        toast.error(err);
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
        const err = 'Only PDF documents are accepted.';
        setUploadAlert({ type: 'error', text: err });
        toast.error(err);
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
      const msg = `Ingested '${selectedFile.name}' (${typeLabel}) — ${data.chunks_created} chunks indexed.`;

      setUploadAlert({ type: 'success', text: msg });
      toast.success(msg);

      if (data.agent) {
        setAgentResult(data.agent);
      }

      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchDocuments();
      fetchPostedNotices();
    } catch (err) {
      setUploadAlert({ type: 'error', text: err.message });
      toast.error(err.message || 'PDF ingestion failed.');
    } finally {
      setIsUploading(false);
      setUploadStep('');
    }
  };

  const handleDeletePrompt = (filename) => {
    setDocToDelete(filename);
  };

  const confirmDeleteDoc = async () => {
    if (!docToDelete) return;
    setIsDeletingDoc(true);

    try {
      await deleteDocumentApi(docToDelete);
      toast.success(`Removed '${docToDelete}' from knowledge base.`);
      setUploadAlert({ type: 'success', text: `Removed '${docToDelete}' from database.` });
      setDocToDelete(null);
      fetchDocuments();
    } catch (err) {
      toast.error(err.message || 'Failed to remove document.');
      setUploadAlert({ type: 'error', text: err.message });
    } finally {
      setIsDeletingDoc(false);
    }
  };

  const handlePostNotice = async (e) => {
    e.preventDefault();
    if (!noticeTitle.trim() || !noticeContent.trim()) {
      const err = 'Both title and content are required.';
      setNoticeAlert({ type: 'error', text: err });
      toast.error(err);
      return;
    }
    setIsPostingNotice(true);
    setNoticeAlert(null);
    setNoticeResult(null);

    try {
      const data = await postNoticeApi(noticeTitle, noticeContent);
      setNoticeResult(data);
      setNoticeAlert({ type: 'success', text: 'Notice posted successfully!' });
      toast.success('Notice broadcasted successfully!');
      setNoticeTitle('');
      setNoticeContent('');
      fetchPostedNotices();
    } catch (err) {
      setNoticeAlert({ type: 'error', text: err.message });
      toast.error(err.message || 'Failed to broadcast notice.');
    } finally {
      setIsPostingNotice(false);
    }
  };

  const confirmDeleteNotice = async () => {
    if (!noticeToDelete) return;
    setIsDeletingNotice(true);
    try {
      await deleteNoticeApi(noticeToDelete.id);
      toast.success(`Deleted notice "${noticeToDelete.title}".`);
      setNoticeToDelete(null);
      fetchPostedNotices();
    } catch (err) {
      toast.error(err.message || 'Failed to delete notice.');
    } finally {
      setIsDeletingNotice(false);
    }
  };

  const handleApproveGap = async (gapId, answer, question) => {
    await approveKnowledgeGapApi(gapId, answer, question);
    fetchGaps();
    fetchDocuments();
    fetchPostedNotices();
  };

  const handleDismissGap = async (gapId) => {
    await dismissKnowledgeGapApi(gapId);
    fetchGaps();
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
      <ConfirmDialog
        open={Boolean(docToDelete)}
        onOpenChange={(open) => { if (!open) setDocToDelete(null); }}
        title="Remove Document from Knowledge Base?"
        description={`Are you sure you want to delete '${docToDelete}'? All vector embeddings associated with this file will be permanently removed.`}
        confirmLabel="Remove Document"
        variant="destructive"
        isLoading={isDeletingDoc}
        onConfirm={confirmDeleteDoc}
      />

      <ConfirmDialog
        open={Boolean(noticeToDelete)}
        onOpenChange={(open) => { if (!open) setNoticeToDelete(null); }}
        title="Delete Broadcast Notice?"
        description={`Are you sure you want to delete "${noticeToDelete?.title}"? All student notifications and associated RAG knowledge chunks will be removed.`}
        confirmLabel="Delete Notice"
        variant="destructive"
        isLoading={isDeletingNotice}
        onConfirm={confirmDeleteNotice}
      />

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
            <button className={`admin-tab-item ${activeTab === 'insights' ? 'active' : ''}`} onClick={() => { setActiveTab('insights'); fetchGaps(); }}>
              <Sparkles className="cm-icon-sm" /> Insights
              {gaps.length > 0 && (
                <span className="admin-tab-badge" style={{ background: '#f59e0b', color: '#1e293b' }}>{gaps.length}</span>
              )}
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
              handleDelete={handleDeletePrompt}
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
              onDeleteNotice={(n) => setNoticeToDelete(n)}
              formatDate={formatDate}
              NOTICE_TYPE_LABELS={NOTICE_TYPE_LABELS}
            />
          )}

          {activeTab === 'insights' && (
            <KnowledgeInsights
              gaps={gaps}
              isLoadingGaps={isLoadingGaps}
              fetchGaps={fetchGaps}
              onApproveGap={handleApproveGap}
              onDismissGap={handleDismissGap}
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
              complaintStaffRoleFilter={complaintStaffRoleFilter}
              setComplaintStaffRoleFilter={setComplaintStaffRoleFilter}
              complaintScopeFilter={complaintScopeFilter}
              setComplaintScopeFilter={setComplaintScopeFilter}
              fetchComplaints={fetchComplaints}
              updateComplaintStatus={updateComplaintStatus}
              updatingComplaintId={updatingComplaintId}
              deleteComplaint={deleteComplaint}
              deletingComplaintId={deletingComplaintId}
              formatDate={formatDate}
            />
          )}
        </div>
      </div>
    </div>
  );
}
