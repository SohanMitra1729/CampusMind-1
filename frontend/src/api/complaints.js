/**
 * src/api/complaints.js — Complaint Management & Hostel Directory API Methods
 */

import { apiClient } from './client';

export async function getHostelsApi() {
  return apiClient('/api/hostels', {
    method: 'GET',
  });
}

export async function classifyComplaintApi(text) {
  return apiClient('/api/complaint/classify', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export async function submitComplaintApi(text, hostelId = null, roomNumber = null) {
  return apiClient('/api/complaint', {
    method: 'POST',
    body: JSON.stringify({
      text,
      hostel_id: hostelId,
      room_number: roomNumber,
    }),
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

export async function getAdminComplaintsApi({ status, category, limit = 50 } = {}) {
  const params = new URLSearchParams();
  if (status && status !== 'all') params.append('status', status);
  if (category && category !== 'all') params.append('category', category);
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
