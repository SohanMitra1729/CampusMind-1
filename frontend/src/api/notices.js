/**
 * src/api/notices.js — Admin Documents, Notices & Notifications API Methods
 */

import { apiClient } from './client';

export async function uploadDocumentApi(file) {
  const formData = new FormData();
  formData.append('file', file);

  return apiClient('/api/admin/upload', {
    method: 'POST',
    body: formData,
  });
}

export async function getDocumentsApi() {
  return apiClient('/api/admin/documents', {
    method: 'GET',
  });
}

export async function deleteDocumentApi(filename) {
  return apiClient(`/api/admin/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export async function postNoticeApi(title, content) {
  return apiClient('/api/admin/notices', {
    method: 'POST',
    body: JSON.stringify({ title, content }),
  });
}

export async function getNoticesListApi() {
  return apiClient('/api/admin/notices-list', {
    method: 'GET',
  });
}

export async function deleteNoticeApi(noticeId) {
  return apiClient(`/api/admin/notices/${noticeId}`, {
    method: 'DELETE',
  });
}

export async function getNotificationsApi() {
  return apiClient('/api/notifications', {
    method: 'GET',
  });
}

export async function markNotificationReadApi(notifId) {
  return apiClient(`/api/notifications/${notifId}/read`, {
    method: 'PATCH',
  });
}

export async function markAllNotificationsReadApi() {
  return apiClient('/api/notifications/read-all', {
    method: 'PATCH',
  });
}

export async function getKnowledgeGapsApi() {
  return apiClient('/api/admin/knowledge-gaps', {
    method: 'GET',
  });
}

export async function approveKnowledgeGapApi(gapId, answer, question) {
  return apiClient(`/api/admin/knowledge-gaps/${gapId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ answer, question }),
  });
}

export async function dismissKnowledgeGapApi(gapId) {
  return apiClient(`/api/admin/knowledge-gaps/${gapId}`, {
    method: 'DELETE',
  });
}

