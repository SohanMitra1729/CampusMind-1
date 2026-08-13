/**
 * src/api/auth.js — Authentication & Admin Auth API Methods
 */

import { apiClient } from './client';

export async function loginApi(identifier, password) {
  return apiClient('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ identifier, password }),
  });
}

export async function signupApi({ name, username, email, scholar_id, password }) {
  return apiClient('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ name, username, email, scholar_id, password }),
  });
}

export async function forgotPasswordApi(identifier) {
  return apiClient('/api/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ identifier }),
  });
}

export async function resetPasswordApi(access_token, password) {
  return apiClient('/api/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({ access_token, password }),
  });
}

export async function adminAuthApi(username, password) {
  return apiClient('/api/admin/auth', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}
