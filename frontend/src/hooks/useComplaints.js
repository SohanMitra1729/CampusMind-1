/**
 * src/hooks/useComplaints.js — Complaints Hook (Classify, Submit & Upvote)
 *
 * Scope: Student-side complaint lifecycle only.
 * Admin complaint management lives in AdminPage.jsx which fetches directly via api/complaints.js.
 */

import { useState, useEffect, useCallback } from 'react';
import { getHostelsApi, classifyComplaintApi, submitComplaintApi, voteComplaintApi, getMyComplaintsApi } from '../api/complaints';

export function useComplaints(userId) {
  const [hostels, setHostels] = useState([]);
  const [hostelError, setHostelError] = useState(null);

  const [complaintPending, setComplaintPending] = useState(null);
  const [complaintSubmitting, setComplaintSubmitting] = useState(false);
  const [complaintResult, setComplaintResult] = useState(null);
  const [votedComplaints, setVotedComplaints] = useState(new Set());

  // Location inputs
  const [selectedHostelId, setSelectedHostelId] = useState('');
  const [roomNumber, setRoomNumber] = useState('');

  // My complaints panel
  const [showMyComplaints, setShowMyComplaints] = useState(false);
  const [myComplaints, setMyComplaints] = useState([]);
  const [myComplaintsLoading, setMyComplaintsLoading] = useState(false);

  // ── Fetch hostels on mount ──────────────────────────────────────────────────
  useEffect(() => {
    getHostelsApi()
      .then(data => {
        setHostels(data || []);
        setHostelError(null);
      })
      .catch((err) => {
        console.error('Failed to load hostels:', err);
        setHostelError('Could not load hostel list. Please refresh and try again.');
      });
  }, []);

  // ── Classify incoming text for complaint detection ──────────────────────────
  const detectComplaint = useCallback((inputText) => {
    if (!userId) return;
    classifyComplaintApi(inputText)
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
      .catch(() => {}); // Classification is best-effort — silent fail is acceptable
  }, [userId]);

  // ── Fetch student's own complaints ─────────────────────────────────────────
  const fetchMyComplaints = useCallback(async () => {
    if (!userId) return;
    setMyComplaintsLoading(true);
    try {
      const data = await getMyComplaintsApi();
      setMyComplaints(data || []);
    } catch (e) {
      console.error('Failed to fetch my complaints', e);
    } finally {
      setMyComplaintsLoading(false);
    }
  }, [userId]);

  // ── Submit a complaint ──────────────────────────────────────────────────────
  const submitComplaint = useCallback(async () => {
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
      const data = await submitComplaintApi(
        complaintPending.text,
        selectedHostelId,
        complaintPending.needsRoom && roomNumber.trim() ? roomNumber.trim() : null
      );
      setComplaintResult(data);
      setComplaintPending(null);
      fetchMyComplaints();
    } catch (err) {
      setComplaintResult({ error: err.message });
      setComplaintPending(null);
    } finally {
      setComplaintSubmitting(false);
    }
  }, [complaintPending, complaintSubmitting, selectedHostelId, roomNumber, fetchMyComplaints]);

  // ── Upvote an existing complaint ───────────────────────────────────────────
  const upvoteComplaint = useCallback(async (complaintId) => {
    if (votedComplaints.has(complaintId)) return;
    try {
      await voteComplaintApi(complaintId);
      setVotedComplaints(prev => new Set([...prev, complaintId]));
      setComplaintResult(prev => prev ? ({
        ...prev,
        similar_complaints: (prev.similar_complaints || []).map(s =>
          s.id === complaintId ? { ...s, vote_count: s.vote_count + 1 } : s
        ),
      }) : prev);
    } catch (err) {
      console.error('Vote error:', err);
    }
  }, [votedComplaints]);

  // ── Reset complaint UI state ────────────────────────────────────────────────
  const resetComplaintState = useCallback(() => {
    setComplaintPending(null);
    setComplaintResult(null);
    setSelectedHostelId('');
    setRoomNumber('');
  }, []);

  return {
    hostels,
    hostelError,
    complaintPending,
    setComplaintPending,
    complaintSubmitting,
    complaintResult,
    votedComplaints,
    selectedHostelId,
    setSelectedHostelId,
    roomNumber,
    setRoomNumber,
    showMyComplaints,
    setShowMyComplaints,
    myComplaints,
    myComplaintsLoading,
    detectComplaint,
    fetchMyComplaints,
    submitComplaint,
    upvoteComplaint,
    resetComplaintState,
  };
}
