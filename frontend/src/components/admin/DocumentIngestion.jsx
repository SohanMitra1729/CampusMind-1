/**
 * src/components/admin/DocumentIngestion.jsx — Knowledge Base & Document Ingestion
 * ─────────────────────────────────────────────────────────────────────────────
 * Provides:
 *   1. System stats (total docs, total pgvector chunks, vector model)
 *   2. Drag & drop PDF uploader with multi-stage animated ingestion stepper
 *   3. Agent intelligence summary report post-ingestion
 *   4. Filterable & searchable Knowledge Base document index table
 */

import { useState, useMemo } from 'react';
import {
  Upload,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Search,
  Database,
  Layers,
  Sparkles,
  Table,
  Tag,
  Users,
  Check,
  ExternalLink,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';
import { API_BASE_URL } from '../../api/client';

const PIPELINE_STEPS = [
  { id: 1, label: 'Upload & Parse', desc: 'Extracting text & table rows' },
  { id: 2, label: 'LLM Taxonomy', desc: 'Classifying category & audience' },
  { id: 3, label: 'Vector Embedding', desc: 'Generating Gemini embeddings' },
  { id: 4, label: 'pgvector Indexing', desc: 'Storing vectors into database' },
  { id: 5, label: 'Agent Dispatch', desc: 'Targeting student notifications' },
];

export default function DocumentIngestion({
  documents = [],
  isLoadingDocs,
  selectedFile,
  fileInputRef,
  handleFileSelect,
  handleDrop,
  handleUpload,
  isUploading,
  uploadStep,
  uploadAlert,
  agentResult,
  handleDelete,
  fetchDocuments,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [isDragOver, setIsDragOver] = useState(false);

  // Calculate totals
  const totalChunks = useMemo(() => {
    return documents.reduce((sum, doc) => sum + (Number(doc.chunks || doc.chunk_count) || 0), 0);
  }, [documents]);

  // Unique categories for filtering
  const categories = useMemo(() => {
    const set = new Set();
    documents.forEach((d) => {
      if (d.category) set.add(d.category);
    });
    return Array.from(set);
  }, [documents]);

  // Filtered documents
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchSearch =
        !searchTerm ||
        (doc.filename && doc.filename.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (doc.title && doc.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (doc.category && doc.category.toLowerCase().includes(searchTerm.toLowerCase())) ||
        (doc.department && doc.department.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchCategory =
        categoryFilter === 'all' ||
        (doc.category && doc.category.toLowerCase() === categoryFilter.toLowerCase());

      return matchSearch && matchCategory;
    });
  }, [documents, searchTerm, categoryFilter]);

  // Determine current active pipeline step index (1..5) from uploadStep string
  const activeStepIndex = useMemo(() => {
    if (!isUploading) return 0;
    const s = uploadStep.toLowerCase();
    if (s.includes('upload') || s.includes('server')) return 1;
    if (s.includes('detect') || s.includes('extract') || s.includes('chunk')) return 2;
    if (s.includes('embed')) return 3;
    if (s.includes('index') || s.includes('pgvector')) return 4;
    if (s.includes('agent') || s.includes('classif') || s.includes('notif')) return 5;
    return 2;
  }, [isUploading, uploadStep]);

  return (
    <div className="admin-tab-content">
      {/* ── Knowledge Base Stats Cards ── */}
      <div className="admin-kb-stats-grid">
        <div className="admin-kb-stat-card">
          <div className="admin-kb-stat-icon-wrapper" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa' }}>
            <FileText className="cm-icon-md" />
          </div>
          <div>
            <div className="admin-kb-stat-value">{documents.length}</div>
            <div className="admin-kb-stat-label">Ingested Documents</div>
          </div>
        </div>

        <div className="admin-kb-stat-card">
          <div className="admin-kb-stat-icon-wrapper" style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
            <Layers className="cm-icon-md" />
          </div>
          <div>
            <div className="admin-kb-stat-value">{totalChunks.toLocaleString()}</div>
            <div className="admin-kb-stat-label">Indexed Vector Chunks</div>
          </div>
        </div>

        <div className="admin-kb-stat-card">
          <div className="admin-kb-stat-icon-wrapper" style={{ background: 'rgba(34, 197, 94, 0.15)', color: '#4ade80' }}>
            <Database className="cm-icon-md" />
          </div>
          <div>
            <div className="admin-kb-stat-value" style={{ fontSize: '15px', fontWeight: 600 }}>pgvector Hybrid RAG</div>
            <div className="admin-kb-stat-label">Gemini Embedding-2 • Ready</div>
          </div>
        </div>
      </div>

      {/* ── Ingestion Section ── */}
      <Card style={{ marginTop: 'var(--space-6)' }}>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Upload className="cm-icon-md text-[var(--cm-accent)]" /> Upload & Ingest PDF Document
          </CardTitle>
          <CardDescription>
            Upload student handbooks, results sheets, fee structures, notices, or hostel allotment PDF files into the pgvector RAG memory.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {uploadAlert && (
            <div
              className={`auth-alert-box ${uploadAlert.type === 'success' ? 'auth-alert-success' : 'auth-alert-error'}`}
              style={{ marginBottom: 'var(--space-4)' }}
            >
              {uploadAlert.type === 'success' ? (
                <CheckCircle2 className="cm-icon-md flex-shrink-0" />
              ) : (
                <AlertCircle className="cm-icon-md flex-shrink-0" />
              )}
              <span>{uploadAlert.text}</span>
            </div>
          )}

          {/* Dropzone */}
          <div
            className={`admin-dropzone ${isDragOver ? 'drag-over' : ''} ${selectedFile ? 'has-file' : ''}`}
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              setIsDragOver(false);
              handleDrop(e);
            }}
            onClick={() => {
              if (!isUploading) fileInputRef.current?.click();
            }}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf"
              style={{ display: 'none' }}
              disabled={isUploading}
            />
            <div className="admin-dropzone-icon-bubble">
              <Upload className="cm-icon-lg" />
            </div>
            <p className="admin-dropzone-title">
              {selectedFile ? selectedFile.name : 'Drag & drop your PDF here, or click to browse'}
            </p>
            <p className="admin-dropzone-subtitle">
              Supports digital PDFs up to 25MB • Result Sheets, Allotments, Circulars, Calendars
            </p>
          </div>

          {/* Selected File Controls */}
          {selectedFile && (
            <div className="admin-selected-file-banner">
              <div className="admin-selected-file-info">
                <FileText className="cm-icon-md text-[var(--cm-accent)] flex-shrink-0" />
                <div>
                  <div className="admin-selected-file-name">{selectedFile.name}</div>
                  <div className="admin-selected-file-meta">
                    {(selectedFile.size / 1024).toFixed(1)} KB • Ready for AI Ingestion
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleFileSelect({ target: { files: [] } });
                  }}
                  disabled={isUploading}
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleUpload();
                  }}
                  isLoading={isUploading}
                  disabled={isUploading}
                >
                  Ingest Document
                </Button>
              </div>
            </div>
          )}

          {/* ── Multi-Stage Pipeline Progress Stepper ── */}
          {isUploading && (
            <div className="admin-pipeline-stepper-container">
              <div className="admin-pipeline-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <RefreshCw className="animate-spin cm-icon-sm text-[var(--cm-accent)]" />
                  <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--cm-fg)' }}>
                    {uploadStep || 'Processing ingestion pipeline...'}
                  </span>
                </div>
                <span className="admin-pipeline-badge">Live Pipeline</span>
              </div>

              <div className="admin-pipeline-steps-row">
                {PIPELINE_STEPS.map((step) => {
                  const isDone = activeStepIndex > step.id;
                  const isCurrent = activeStepIndex === step.id;
                  return (
                    <div
                      key={step.id}
                      className={`admin-pipeline-step-item ${isDone ? 'done' : isCurrent ? 'current' : 'pending'}`}
                    >
                      <div className="admin-pipeline-step-indicator">
                        {isDone ? (
                          <Check className="cm-icon-xs" />
                        ) : isCurrent ? (
                          <RefreshCw className="animate-spin cm-icon-xs" />
                        ) : (
                          <span>{step.id}</span>
                        )}
                      </div>
                      <div className="admin-pipeline-step-text">
                        <div className="admin-pipeline-step-label">{step.label}</div>
                        <div className="admin-pipeline-step-desc">{step.desc}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Agent Ingestion Report ── */}
          {agentResult && (
            <div className="admin-agent-report-card">
              <div className="admin-agent-report-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles className="cm-icon-sm text-yellow-400" />
                  <span style={{ fontWeight: 600, fontSize: '13px' }}>Agent Ingestion Intelligence Summary</span>
                </div>
                <span className="admin-agent-report-badge">AI Verified</span>
              </div>

              <div className="admin-agent-report-grid">
                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Detected Category</span>
                  <span className="admin-agent-field-val" style={{ textTransform: 'capitalize' }}>
                    {agentResult.doc_type || agentResult.category || 'General'}
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Content Structure</span>
                  <span className="admin-agent-field-val">
                    {agentResult.contentType === 'tabular' ? 'Tabular (Row Sentences)' : 'Text Paragraphs'}
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Chunks Stored</span>
                  <span className="admin-agent-field-val" style={{ color: 'var(--cm-accent)', fontWeight: 700 }}>
                    {agentResult.chunksCreated || agentResult.chunks_created || 'Indexed'}
                  </span>
                </div>

                <div className="admin-agent-report-field">
                  <span className="admin-agent-field-label">Notification Action</span>
                  <span className="admin-agent-field-val">
                    {(agentResult.notifications_sent > 0 || agentResult.notified > 0) ? (
                      <span style={{ color: '#4ade80' }}>
                        {agentResult.is_broadcast !== false ? '🌐 Broadcasted to all students' : `🎯 Dispatched to ${agentResult.notifications_sent || agentResult.notified} student(s)`}
                      </span>
                    ) : (agentResult.notification_skipped || agentResult.skipped) ? (
                      <span style={{ color: 'var(--cm-muted)' }}>ℹ️ Reference Doc (No notification triggered)</span>
                    ) : (
                      <span style={{ color: '#60a5fa' }}>📢 Broadcasted to all students</span>
                    )}
                  </span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Knowledge Base Index Table ── */}
      <Card style={{ marginTop: 'var(--space-6)' }}>
        <CardHeader style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-4)' }}>
          <div>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <FileText className="cm-icon-md text-[var(--cm-accent)]" /> Knowledge Base Index ({documents.length})
            </CardTitle>
            <CardDescription>
              Active document chunks stored in PostgreSQL vector database with Gemini embeddings.
            </CardDescription>
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-2)', alignItems: 'center', flexWrap: 'wrap' }}>
            {/* Search Input */}
            <div className="admin-search-wrapper">
              <Search className="admin-search-icon cm-icon-xs" />
              <input
                type="text"
                placeholder="Search documents..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="admin-search-input"
              />
            </div>

            {/* Category Filter */}
            {categories.length > 0 && (
              <select
                className="admin-filter-select"
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
              >
                <option value="all">All Categories</option>
                {categories.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat.charAt(0).toUpperCase() + cat.slice(1)}
                  </option>
                ))}
              </select>
            )}

            {/* Refresh Button */}
            <Button variant="ghost" size="sm" onClick={fetchDocuments} title="Reload knowledge base index">
              <RefreshCw className="cm-icon-sm mr-1" /> Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {isLoadingDocs ? (
            <div className="admin-empty-state">
              <RefreshCw className="animate-spin cm-icon-lg mx-auto mb-3 text-[var(--cm-accent)]" />
              <p style={{ fontWeight: 500 }}>Querying pgvector vector store...</p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)' }}>Retrieving chunk clusters and document metadata</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="admin-empty-state">
              <Database className="cm-icon-xl mx-auto mb-3 text-[var(--cm-muted)]" />
              <p style={{ fontWeight: 600, fontSize: '15px' }}>No documents ingested yet</p>
              <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', maxWidth: '400px', margin: '4px auto 0' }}>
                Upload university documents such as result sheets, fee circulars, or timetables to populate the CampusMind RAG memory.
              </p>
            </div>
          ) : filteredDocuments.length === 0 ? (
            <div className="admin-empty-state">
              <Search className="cm-icon-lg mx-auto mb-2 text-[var(--cm-muted)]" />
              <p>No documents match your search query "{searchTerm}".</p>
              <Button variant="ghost" size="xs" onClick={() => { setSearchTerm(''); setCategoryFilter('all'); }} style={{ marginTop: '8px' }}>
                Clear Filters
              </Button>
            </div>
          ) : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th style={{ minWidth: '280px' }}>Document / Title</th>
                    <th style={{ minWidth: '150px' }}>Structure</th>
                    <th style={{ minWidth: '130px' }}>Category</th>
                    <th style={{ minWidth: '160px' }}>Target Audience</th>
                    <th style={{ minWidth: '130px', textAlign: 'center' }}>Vector Chunks</th>
                    <th style={{ minWidth: '140px', textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredDocuments.map((doc, idx) => {
                    const isTabular = doc.content_type === 'tabular';
                    const chunkCount = Number(doc.chunks || doc.chunk_count) || 1;
                    return (
                      <tr key={idx} className="admin-table-row-hover">
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                            <div
                              className="admin-doc-type-icon"
                              style={{
                                background: isTabular ? 'rgba(16, 185, 129, 0.12)' : 'rgba(59, 130, 246, 0.12)',
                                color: isTabular ? '#34d399' : '#60a5fa',
                              }}
                            >
                              {isTabular ? <Table size={16} /> : <FileText size={16} />}
                            </div>
                            <div>
                              <div style={{ fontWeight: 600, color: 'var(--cm-fg)', fontSize: '13px' }}>
                                {doc.title || doc.filename}
                              </div>
                              <div style={{ fontSize: '11px', color: 'var(--cm-muted)', fontFamily: 'monospace' }}>
                                {doc.filename}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td>
                          <span
                            className="admin-badge-pill"
                            style={{
                              background: isTabular ? 'rgba(16, 185, 129, 0.12)' : 'rgba(99, 102, 241, 0.12)',
                              color: isTabular ? '#34d399' : '#818cf8',
                              border: `1px solid ${isTabular ? 'rgba(16, 185, 129, 0.3)' : 'rgba(99, 102, 241, 0.3)'}`,
                            }}
                          >
                            {isTabular ? 'Tabular (Tables)' : 'Text Document'}
                          </span>
                        </td>

                        <td>
                          <span
                            className="admin-badge-pill"
                            style={{
                              background: 'rgba(255, 255, 255, 0.05)',
                              color: 'var(--cm-fg)',
                              border: '1px solid var(--cm-border)',
                              textTransform: 'capitalize',
                            }}
                          >
                            <Tag size={10} style={{ marginRight: '4px' }} />
                            {doc.category || 'general'}
                          </span>
                        </td>

                        <td>
                          <div style={{ fontSize: '12px', color: 'var(--cm-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <Users size={12} /> {doc.audience || doc.department || 'All Students'}
                          </div>
                        </td>

                        <td style={{ textAlign: 'center' }}>
                          <span className="admin-chunk-count-badge">
                            {chunkCount.toLocaleString()} chunks
                          </span>
                        </td>

                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', justifyContent: 'flex-end' }}>
                            {doc.filename?.endsWith('.pdf') && (
                              <Button
                                variant="secondary"
                                size="xs"
                                onClick={() => window.open(`${API_BASE_URL}/api/documents/${encodeURIComponent(doc.filename)}/view`, '_blank', 'noopener,noreferrer')}
                                title="Open original PDF in new tab"
                              >
                                <ExternalLink size={13} style={{ marginRight: '4px' }} /> PDF
                              </Button>
                            )}
                            <Button
                              variant="ghost"
                              size="xs"
                              onClick={() => handleDelete(doc.filename || doc.source)}
                              style={{ color: 'var(--cm-error)' }}
                              title="Delete all chunks from pgvector"
                            >
                              <Trash2 size={13} style={{ marginRight: '4px' }} /> Delete
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
