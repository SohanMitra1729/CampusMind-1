/**
 * src/components/admin/DocumentIngestion.jsx — Knowledge Base Upload & Management
 */

import { Upload, FileText, Trash2, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../ui/Card';
import { Button } from '../ui/Button';

export default function DocumentIngestion({
  documents,
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
  return (
    <div className="admin-tab-content">
      <Card>
        <CardHeader>
          <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
            <Upload className="cm-icon-md text-[var(--cm-accent)]" /> Upload PDF Document
          </CardTitle>
          <CardDescription>
            Ingest university handbooks, notices, or timetables into pgvector RAG memory.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {uploadAlert && (
            <div className={`auth-alert-box ${uploadAlert.type === 'success' ? 'auth-alert-success' : 'auth-alert-error'}`} style={{ marginBottom: 'var(--space-4)' }}>
              {uploadAlert.type === 'success' ? <CheckCircle2 className="cm-icon-md flex-shrink-0" /> : <AlertCircle className="cm-icon-md flex-shrink-0" />}
              <span>{uploadAlert.text}</span>
            </div>
          )}

          <div
            className="admin-dropzone"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              accept=".pdf"
              style={{ display: 'none' }}
            />
            <Upload className="cm-icon-xl text-[var(--cm-muted)] mb-2" />
            <p className="font-medium text-[var(--cm-fg)] mb-1">
              {selectedFile ? selectedFile.name : 'Drag & drop PDF here, or click to browse'}
            </p>
            <p className="text-xs text-[var(--cm-muted)]">Supported: PDF files up to 20MB</p>
          </div>

          {selectedFile && (
            <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'flex-end', gap: 'var(--space-2)' }}>
              <Button variant="ghost" onClick={() => handleFileSelect({ target: { files: [] } })} disabled={isUploading}>
                Cancel
              </Button>
              <Button onClick={handleUpload} isLoading={isUploading} disabled={isUploading}>
                Ingest Document
              </Button>
            </div>
          )}

          {isUploading && (
            <div style={{ marginTop: 'var(--space-3)', fontSize: 'var(--text-xs)', color: 'var(--cm-accent)', display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <RefreshCw className="animate-spin cm-icon-xs" /> {uploadStep}
            </div>
          )}

          {agentResult && (
            <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-3)', borderRadius: 'var(--radius-md)', background: 'var(--cm-secondary)', border: '1px solid var(--cm-border)', fontSize: 'var(--text-xs)' }}>
              <div style={{ fontWeight: 'var(--font-semibold)', marginBottom: 'var(--space-1)' }}>🤖 Agent Summary</div>
              <div>Detected Type: <strong>{agentResult.content_type || 'general'}</strong></div>
              <div>Extracted Title: <strong>{agentResult.extracted_title || 'N/A'}</strong></div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card style={{ marginTop: 'var(--space-6)' }}>
        <CardHeader style={{ display: 'flex', flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <CardTitle style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
              <FileText className="cm-icon-md text-[var(--cm-accent)]" /> Knowledge Base Index ({documents.length})
            </CardTitle>
            <CardDescription>Active document chunks stored in PostgreSQL vector database.</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={fetchDocuments}>
            <RefreshCw className="cm-icon-sm mr-1" /> Refresh
          </Button>
        </CardHeader>
        <CardContent>
          {isLoadingDocs ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              <RefreshCw className="animate-spin cm-icon-md mx-auto mb-2" /> Loading documents...
            </div>
          ) : documents.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--space-6)', color: 'var(--cm-muted)' }}>
              No documents ingested yet. Upload a PDF above to build your RAG memory!
            </div>
          ) : (
            <div className="admin-table-wrapper">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Chunks</th>
                    <th>Ingested At</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {documents.map((doc, idx) => (
                    <tr key={idx}>
                      <td style={{ fontWeight: 'var(--font-medium)' }}>📄 {doc.source || doc.filename || 'Document'}</td>
                      <td>{doc.content_type || 'pdf'}</td>
                      <td>{doc.chunk_count || 1}</td>
                      <td>{doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}</td>
                      <td style={{ textAlign: 'right' }}>
                        <Button variant="ghost" size="xs" onClick={() => handleDelete(doc.source || doc.filename)} style={{ color: 'var(--cm-error)' }}>
                          <Trash2 className="cm-icon-xs" /> Delete
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
  );
}
