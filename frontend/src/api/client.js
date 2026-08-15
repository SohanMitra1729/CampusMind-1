/**
 * src/api/client.js — Centralized Fetch API Client
 * ─────────────────────────────────────────────────
 * Handles:
 *  - Dynamic VITE_API_URL resolution
 *  - Automatic Bearer token insertion (Student JWT / Admin Secret)
 *  - Standardized JSON parsing & HTTP error handling
 */

export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Base HTTP request helper
 * @param {string} endpoint - e.g. "/api/auth/login"
 * @param {Object} options - fetch options (method, headers, body, etc.)
 */
export async function apiClient(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const headers = {
    ...options.headers,
  };

  // If body is NOT FormData, default to application/json
  if (!(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  // Attach token if present and not already provided
  if (!headers['Authorization']) {
    let studentToken = sessionStorage.getItem('sb-access-token');
    if (!studentToken) {
      try {
        const storedSession = localStorage.getItem('campusmind_session');
        if (storedSession) {
          const session = JSON.parse(storedSession);
          studentToken = session?.access_token;
          if (studentToken) {
            sessionStorage.setItem('sb-access-token', studentToken);
          }
        }
      } catch {
        // ignore JSON parse error
      }
    }

    const adminToken = sessionStorage.getItem('campusmind_admin_token') || sessionStorage.getItem('admin-token');

    if (endpoint.startsWith('/api/admin') && adminToken) {
      headers['Authorization'] = `Bearer ${adminToken}`;
    } else if (studentToken) {
      headers['Authorization'] = `Bearer ${studentToken}`;
    }
  }

  const config = {
    ...options,
    headers,
  };

  const response = await fetch(url, config);

  // Handle empty or 204 No Content responses
  if (response.status === 204) {
    return null;
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorMessage = data.detail || data.message || `Request failed with status ${response.status}`;
    const error = new Error(errorMessage);
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}
