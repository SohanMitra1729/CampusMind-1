/**
 * src/api/complaints.js — Complaint Management API Methods
 *
 * Note: Complaint filing (classify + submit) is now handled server-side through
 * the chat endpoint via the conversational complaint dialogue agent.
 * This file only contains: hostel list, voting, and viewing complaints.
 */

import { apiClient } from './client';

export async function getHostelsApi() {
  return apiClient('/api/hostels', {
    method: 'GET',
  });
}

export async function voteComplaintApi(complaintId) {
  return apiClient(`/api/complaint/${complaintId}/vote`, {
    method: 'POST',
  });
}

export async function getMyComplaintsApi() {
  return apiClient('/api/my-complaints', {
    method: 'GET',
  });
}

export async function getAdminComplaintsApi({ status, category, staffRole, scope, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.append('status', status);
  if (category && category !== 'all') params.append('category', category);
  if (staffRole && staffRole !== 'all') params.append('staff_role', staffRole);
  if (scope && scope !== 'all') params.append('scope', scope);
  params.append('limit', limit);

  const queryString = params.toString();
  const endpoint = `/api/admin/complaints${queryString ? `?${queryString}` : ''}`;
  return apiClient(endpoint, {
    method: 'GET',
  });
}

export async function updateComplaintStatusApi(complaintId, status) {
  return apiClient(`/api/admin/complaints/${complaintId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  });
}
