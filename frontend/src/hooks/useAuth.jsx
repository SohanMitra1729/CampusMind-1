/**
 * src/hooks/useAuth.js — Authentication State & Actions Hook
 */

import { useState, useCallback, createContext, useContext } from 'react';
import { loginApi, signupApi, forgotPasswordApi, resetPasswordApi, adminAuthApi } from '../api/auth';

const AuthContext = createContext(null);

function getInitialUser() {
  const storedUser = localStorage.getItem('campusmind_user');
  const storedSession = localStorage.getItem('campusmind_session');

  if (storedUser && storedSession) {
    try {
      const session = JSON.parse(storedSession);
      const now = Math.floor(Date.now() / 1000);
      if (session.expires_at && session.expires_at > now) {
        if (session.access_token && !sessionStorage.getItem('sb-access-token')) {
          sessionStorage.setItem('sb-access-token', session.access_token);
        }
        return JSON.parse(storedUser);
      }
    } catch {
      // Ignore JSON parse error
    }
    localStorage.removeItem('campusmind_user');
    localStorage.removeItem('campusmind_session');
  }
  return null;
}

function getInitialAdminToken() {
  return sessionStorage.getItem('campusmind_admin_token') || sessionStorage.getItem('admin-token');
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getInitialUser);
  const [adminToken, setAdminToken] = useState(getInitialAdminToken);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const login = useCallback(async (identifier, password) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await loginApi(identifier, password);
      if (data.session?.access_token) {
        sessionStorage.setItem('sb-access-token', data.session.access_token);
      }
      localStorage.setItem('campusmind_session', JSON.stringify(data.session));
      localStorage.setItem('campusmind_user', JSON.stringify(data.user));
      setUser(data.user);
      return data.user;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signup = useCallback(async ({ name, username, email, scholar_id, password }) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await signupApi({ name, username, email, scholar_id, password });
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const forgotPassword = useCallback(async (identifier) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await forgotPasswordApi(identifier);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const resetPassword = useCallback(async (access_token, password) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await resetPasswordApi(access_token, password);
      return data;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const adminLogin = useCallback(async (username, password) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await adminAuthApi(username, password);
      const token = data.token;
      sessionStorage.setItem('campusmind_admin_token', token);
      sessionStorage.setItem('admin-token', token);
      setAdminToken(token);
      return token;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    setUser(null);
    localStorage.removeItem('campusmind_user');
    localStorage.removeItem('campusmind_session');
    sessionStorage.removeItem('sb-access-token');
  }, []);

  const adminLogout = useCallback(() => {
    setAdminToken(null);
    sessionStorage.removeItem('campusmind_admin_token');
    sessionStorage.removeItem('admin-token');
  }, []);

  const value = {
    user,
    adminToken,
    isLoading,
    error,
    login,
    signup,
    forgotPassword,
    resetPassword,
    adminLogin,
    logout,
    adminLogout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
