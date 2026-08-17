/**
 * App.jsx — Application Router, Custom Hooks & Page Containers
 * ─────────────────────────────────────────────────────────────
 * Route Structure:
 *   /            ➔ ChatPage (Protected route)
 *   /auth        ➔ AuthPage (Public)
 *   /admin/login ➔ AdminLoginPage (Public)
 *   /admin       ➔ AdminPage (Protected route)
 */

import { useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import ChatPage from './pages/ChatPage';
import AuthPage from './pages/AuthPage';
import AdminLoginPage from './pages/AdminLoginPage';
import AdminPage from './pages/AdminPage';
import { useAuth, AuthProvider } from './hooks/useAuth';
import './index.css';

function AppRoutes() {
  const { user, adminToken, logout, adminLogout } = useAuth();
  const navigate = useNavigate();

  const handleAuthSuccess = useCallback(() => {
    navigate('/', { replace: true });
  }, [navigate]);

  const handleLogout = useCallback(() => {
    logout();
    navigate('/auth', { replace: true });
  }, [logout, navigate]);

  const handleAdminSuccess = useCallback(() => {
    navigate('/admin', { replace: true });
  }, [navigate]);

  const handleAdminLogout = useCallback(() => {
    adminLogout();
    navigate('/admin/login', { replace: true });
  }, [adminLogout, navigate]);

  return (
    <Routes>
      {/* Student Chat (Protected) */}
      <Route
        path="/"
        element={
          user ? (
            <ChatPage user={user} onLogout={handleLogout} />
          ) : (
            <Navigate to="/auth" replace />
          )
        }
      />

      {/* Student Auth */}
      <Route
        path="/auth"
        element={
          user ? (
            <Navigate to="/" replace />
          ) : (
            <AuthPage onAuthSuccess={handleAuthSuccess} />
          )
        }
      />

      {/* Admin Login */}
      <Route
        path="/admin/login"
        element={
          adminToken ? (
            <Navigate to="/admin" replace />
          ) : (
            <AdminLoginPage onAdminSuccess={handleAdminSuccess} />
          )
        }
      />

      {/* Admin Dashboard (Protected) */}
      <Route
        path="/admin"
        element={
          adminToken ? (
            <AdminPage onBack={handleAdminLogout} />
          ) : (
            <Navigate to="/admin/login" replace />
          )
        }
      />

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster richColors position="top-right" theme="dark" closeButton />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
