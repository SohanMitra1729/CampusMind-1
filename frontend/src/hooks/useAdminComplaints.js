/**
 * src/hooks/useAdminComplaints.js — Admin Complaint Management Hook
 *
 * Handles admin-side complaint state: fetching, filtering, and status updates.
 * Extracted from AdminPage.jsx to keep the page component lean.
 */

import { useState, useCallback } from 'react';
import { getAdminComplaintsApi, updateComplaintStatusApi } from '../api/complaints';

export function useAdminComplaints() {
  const [complaints, setComplaints] = useState([]);
  const [isLoadingComplaints, setIsLoadingComplaints] = useState(false);
  const [complaintStatusFilter, setComplaintStatusFilter] = useState('');
  const [complaintCategoryFilter, setComplaintCategoryFilter] = useState('');
  const [updatingComplaintId, setUpdatingComplaintId] = useState(null);

  const fetchComplaints = useCallback(async (status = '', category = '') => {
    setIsLoadingComplaints(true);
    try {
      const data = await getAdminComplaintsApi({ status, category });
      setComplaints(data || []);
    } catch (e) {
      console.error('Failed to load complaints', e);
    } finally {
      setIsLoadingComplaints(false);
    }
  }, []);

  const updateComplaintStatus = useCallback(async (complaintId, newStatus) => {
    setUpdatingComplaintId(complaintId);
    try {
      await updateComplaintStatusApi(complaintId, newStatus);
      setComplaints(prev =>
        prev
          .map(comp => comp.id === complaintId ? { ...comp, status: newStatus } : comp)
          .filter(item => !complaintStatusFilter || item.status === complaintStatusFilter)
      );
    } catch (e) {
      console.error('Failed to update complaint status', e);
    } finally {
      setUpdatingComplaintId(null);
    }
  }, [complaintStatusFilter]);

  return {
    complaints,
    isLoadingComplaints,
    complaintStatusFilter,
    setComplaintStatusFilter,
    complaintCategoryFilter,
    setComplaintCategoryFilter,
    updatingComplaintId,
    fetchComplaints,
    updateComplaintStatus,
  };
}
