/**
 * src/hooks/useComplaints.js — Complaints Hook (Classify, Submit, Upvote & Admin Actions)
 */

import { useState, useEffect, useCallback } from 'react';
import { getHostelsApi, classifyComplaintApi, submitComplaintApi, voteComplaintApi, getMyComplaintsApi, getAdminComplaintsApi, updateComplaintStatusApi } from '../api/complaints';

export function useComplaints(userId) {
  const [hostels, setHostels] = useState([]);
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

  // Admin complaints
  const [adminComplaints, setAdminComplaints] = useState([]);
  const [isLoadingAdminComplaints, setIsLoadingAdminComplaints] = useState(false);
  const [complaintStatusFilter, setComplaintStatusFilter] = useState('');
  const [complaintCategoryFilter, setComplaintCategoryFilter] = useState('');
  const [updatingComplaintId, setUpdatingComplaintId] = useState(null);

  useEffect(() => {
    getHostelsApi()
      .then(data => setHostels(data || []))
      .catch(() => {});
  }, []);

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
      .catch(() => {});
  }, [userId]);

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

  const fetchAdminComplaints = useCallback(async (status = '', category = '') => {
    setIsLoadingAdminComplaints(true);
    try {
      const data = await getAdminComplaintsApi({ status, category });
      setAdminComplaints(data || []);
    } catch (e) {
      console.error('Failed to load complaints', e);
    } finally {
      setIsLoadingAdminComplaints(false);
    }
  }, []);

  const updateComplaintStatus = useCallback(async (complaintId, newStatus) => {
    setUpdatingComplaintId(complaintId);
    try {
      await updateComplaintStatusApi(complaintId, newStatus);
      setAdminComplaints(prev => prev.map(comp => 
        comp.id === complaintId ? { ...comp, status: newStatus } : comp
      ).filter(item => !complaintStatusFilter || item.status === complaintStatusFilter));
    } catch (e) {
      console.error('Failed to update status', e);
    } finally {
      setUpdatingComplaintId(null);
    }
  }, [complaintStatusFilter]);

  const resetComplaintState = useCallback(() => {
    setComplaintPending(null);
    setComplaintResult(null);
    setSelectedHostelId('');
    setRoomNumber('');
  }, []);

  return {
    hostels,
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
    adminComplaints,
    isLoadingAdminComplaints,
    complaintStatusFilter,
    setComplaintStatusFilter,
    complaintCategoryFilter,
    setComplaintCategoryFilter,
    updatingComplaintId,
    detectComplaint,
    fetchMyComplaints,
    submitComplaint,
    upvoteComplaint,
    fetchAdminComplaints,
    updateComplaintStatus,
    resetComplaintState,
  };
}
