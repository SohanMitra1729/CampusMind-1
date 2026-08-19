/**
 * src/components/admin/KnowledgeInsights.jsx — AI Continuous Learning & FAQ Ingestion
 */

import { useState } from 'react';
import { Sparkles, HelpCircle, Trash2, RefreshCw, Send, Flame, Calendar, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/Button';

export default function KnowledgeInsights({
  gaps = [],
  isLoadingGaps,
  fetchGaps,
  onApproveGap,
  onDismissGap,
}) {
  const [activeAnswers, setActiveAnswers] = useState({});
  const [submittingId, setSubmittingId] = useState(null);

  const handleAnswerChange = (gapId, text) => {
    setActiveAnswers((prev) => ({ ...prev, [gapId]: text }));
  };

  const handleApprove = async (gap) => {
    const answer = activeAnswers[gap.id]?.trim() || gap.suggested_answer?.trim();
    if (!answer) {
      toast.error('Please enter the official answer before vectorizing.');
      return;
    }
    setSubmittingId(gap.id);
    try {
      await onApproveGap(gap.id, answer, gap.query);
      toast.success('FAQ successfully vectorized into pgvector knowledge base!');
      setActiveAnswers((prev) => {
        const next = { ...prev };
        delete next[gap.id];
        return next;
      });
    } catch (e) {
      toast.error(e.message || 'Failed to ingest FAQ.');
    } finally {
      setSubmittingId(null);
    }
  };

  const handleDismiss = async (gapId) => {
    try {
      await onDismissGap(gapId);
      toast.success('Query dismissed.');
    } catch (e) {
      toast.error(e.message || 'Failed to dismiss query.');
    }
  };

  const formatDate = (iso) => {
    if (!iso) return 'Recent';
    return new Date(iso).toLocaleDateString('en-IN', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  };

  return (
    <div className="admin-tab-content">
      {/* ── Hero Banner ── */}
      <div className="insights-hero-banner">
        <div className="insights-hero-left">
          <div className="insights-hero-icon-bubble">
            <Sparkles className="cm-icon-md" />
          </div>
          <div>
            <div className="insights-hero-title">
              Continuous Learning & Knowledge Gaps
              {gaps.length > 0 && (
                <span className="insights-pending-pill">
                  <span className="insights-pending-dot" />
                  {gaps.length} Pending
                </span>
              )}
            </div>
            <p className="insights-hero-subtitle">
              Unanswered campus inquiries automatically captured from student chats. Enter the official response to teach CampusMind instantly.
            </p>
          </div>
        </div>
        <Button variant="secondary" size="sm" onClick={fetchGaps} disabled={isLoadingGaps}>
          <RefreshCw className={`cm-icon-sm mr-2 ${isLoadingGaps ? 'animate-spin' : ''}`} /> Refresh
        </Button>
      </div>

      {/* ── Content Area ── */}
      {isLoadingGaps ? (
        <div style={{ textAlign: 'center', padding: 'var(--space-12)', color: 'var(--cm-muted)' }}>
          <RefreshCw className="animate-spin cm-icon-lg mx-auto mb-3 text-sky-400" />
          <p style={{ fontSize: 'var(--text-sm)' }}>Loading knowledge insights...</p>
        </div>
      ) : gaps.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: 'var(--space-12) var(--space-6)',
            background: 'rgba(18, 18, 23, 0.5)',
            borderRadius: 'var(--radius-xl)',
            border: '1px dashed rgba(255, 255, 255, 0.1)',
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto var(--space-4)',
              color: '#34d399',
            }}
          >
            <CheckCircle2 className="cm-icon-lg" />
          </div>
          <h3 style={{ fontWeight: '600', fontSize: 'var(--text-base)', color: 'var(--cm-fg)', marginBottom: '6px' }}>
            All Student Questions Are Covered!
          </h3>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)', maxWidth: 440, margin: '0 auto' }}>
            When students ask questions with no existing answers in documents or circulars, they will automatically appear here for 1-click ingestion.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
          {gaps.map((gap) => {
            const isSubmitting = submittingId === gap.id;
            const currentAnswer = activeAnswers[gap.id] ?? (gap.suggested_answer || '');

            return (
              <div key={gap.id} className="insights-gap-card">
                <div className="insights-gap-header">
                  <div className="insights-gap-query-box">
                    <HelpCircle className="cm-icon-sm insights-gap-query-icon" />
                    <div>
                      <div className="insights-gap-query-text">"{gap.query}"</div>
                      {gap.alternate_queries && gap.alternate_queries.length > 0 && (
                        <div style={{ fontSize: '11px', color: 'var(--cm-muted)', marginTop: '4px', fontStyle: 'italic' }}>
                          Also asked as: {gap.alternate_queries.map((q) => `"${q}"`).join(', ')}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="insights-gap-badges">
                    {gap.frequency > 1 && (
                      <span className="insights-badge-frequency">
                        <Flame className="cm-icon-xs" /> Asked {gap.frequency}x
                      </span>
                    )}
                    <span className="insights-badge-date">
                      <Calendar className="cm-icon-xs inline mr-1 opacity-70" />
                      {formatDate(gap.created_at)}
                    </span>
                  </div>
                </div>

                <div className="insights-textarea-wrapper">
                  <textarea
                    className="insights-textarea"
                    placeholder="Type the official answer or institutional guidance here..."
                    value={currentAnswer}
                    onChange={(e) => handleAnswerChange(gap.id, e.target.value)}
                    rows={3}
                  />
                </div>

                <div className="insights-card-actions">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDismiss(gap.id)}
                    disabled={isSubmitting}
                    style={{ color: 'var(--cm-muted)' }}
                  >
                    <Trash2 className="cm-icon-xs mr-1 text-red-400" /> Dismiss
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleApprove(gap)}
                    disabled={isSubmitting}
                  >
                    <Send className="cm-icon-xs mr-1" />
                    {isSubmitting ? 'Vectorizing...' : 'Approve & Vectorize into RAG'}
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
