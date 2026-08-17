/**
 * src/hooks/useComplaints.js — Student Complaints Viewer Hook
 *
 * Scope: Viewing own complaint history and upvoting existing complaints.
 * Filing new complaints is now handled entirely by the AI chat assistant.
 */

import { useState, useCallback } from 'react';
import { toast } from 'sonner';
import { voteComplaintApi, getMyComplaintsApi } from '../api/complaints';

export function useComplaints(userId) {
  const [votedComplaints, setVotedComplaints] = useState(new Set());

  // My complaints panel
  const [showMyComplaints, setShowMyComplaints] = useState(false);
  const [myComplaints, setMyComplaints] = useState([]);
  const [myComplaintsLoading, setMyComplaintsLoading] = useState(false);

  // ── Fetch student’s own complaints ──────────────────────────────────────
  const fetchMyComplaints = useCallback(async () => {
    if (!userId) return;
    setMyComplaintsLoading(true);
    try {
      const data = await getMyComplaintsApi();
      setMyComplaints(data || []);
    } catch (e) {
      console.error('Failed to fetch my complaints', e);
      toast.error('Failed to load your complaints.');
    } finally {
      setMyComplaintsLoading(false);
    }
  }, [userId]);

  // ── Upvote an existing complaint ───────────────────────────────────────
  const upvoteComplaint = useCallback(async (complaintId) => {
    if (votedComplaints.has(complaintId)) {
      toast.info('You have already upvoted this complaint.');
      return;
    }
    try {
      await voteComplaintApi(complaintId);
      setVotedComplaints(prev => new Set([...prev, complaintId]));
      setMyComplaints(prev =>
        prev.map(c =>
          c.id === complaintId ? { ...c, vote_count: (c.vote_count || 0) + 1 } : c
        )
      );
      toast.success('Complaint upvoted! 👍');
    } catch (err) {
      console.error('Vote error:', err);
      toast.error(err.message || 'Failed to upvote complaint.');
    }
  }, [votedComplaints]);

  return {
    votedComplaints,
    showMyComplaints,
    setShowMyComplaints,
    myComplaints,
    myComplaintsLoading,
    fetchMyComplaints,
    upvoteComplaint,
  };
}
