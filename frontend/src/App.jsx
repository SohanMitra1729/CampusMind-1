import { useState, useEffect } from 'react';
import Chat from './Chat';
import Auth from './Auth';
import Admin from './Admin';
import AdminLogin from './AdminLogin';
import './index.css';

function App() {
  const [user, setUser] = useState(null);
  const [resetToken, setResetToken] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);

  // Admin-specific state — completely separate from user state
  const [isAdminRoute, setIsAdminRoute] = useState(false);
  const [adminAuthenticated, setAdminAuthenticated] = useState(false);
  const [adminToken, setAdminToken] = useState(null);

  useEffect(() => {
    // ── Regular user session ────────────────────────────────────────────────
    const storedUser = localStorage.getItem('campusmind_user');
    const storedSession = localStorage.getItem('campusmind_session');

    if (storedUser && storedSession) {
      const session = JSON.parse(storedSession);
      const now = Math.floor(Date.now() / 1000);
      if (session.expires_at && session.expires_at > now) {
        setUser(JSON.parse(storedUser));
      } else {
        localStorage.removeItem('campusmind_user');
        localStorage.removeItem('campusmind_session');
      }
    }

    // ── Password reset token ────────────────────────────────────────────────
    const hash = window.location.hash;
    if (hash) {
      const params = new URLSearchParams(hash.substring(1));
      const accessToken = params.get('access_token');
      const type = params.get('type');
      if (accessToken && type === 'recovery') {
        setResetToken(accessToken);
      }
    }

    // ── Admin route detection ───────────────────────────────────────────────
    // Admin panel is accessed ONLY via the secret URL hash: /#admin-login
    if (window.location.hash === '#admin-login') {
      setIsAdminRoute(true);
      // Restore admin session from sessionStorage (cleared on tab close)
      const storedAdminToken = sessionStorage.getItem('campusmind_admin_token');
      if (sessionStorage.getItem('campusmind_admin') === 'true' && storedAdminToken) {
        setAdminAuthenticated(true);
        setAdminToken(storedAdminToken);
      }
    }

    setCheckingSession(false);
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('campusmind_user');
    localStorage.removeItem('campusmind_session');
    setUser(null);
  };

  const handleAdminLogout = () => {
    sessionStorage.removeItem('campusmind_admin');
    sessionStorage.removeItem('campusmind_admin_token');
    setAdminAuthenticated(false);
    setAdminToken(null);
    // Navigate away from admin route
    window.history.replaceState(null, null, window.location.pathname);
    setIsAdminRoute(false);
  };

  if (checkingSession) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', color: '#94a3b8' }}>
        Loading...
      </div>
    );
  }

  // ── ADMIN FLOW (completely separate from regular users) ─────────────────────
  if (isAdminRoute) {
    if (!adminAuthenticated) {
      return <AdminLogin onAdminSuccess={(token) => { setAdminAuthenticated(true); setAdminToken(token); }} />;
    }
    return <Admin adminToken={adminToken} onBack={handleAdminLogout} />;
  }

  // ── REGULAR USER FLOW ───────────────────────────────────────────────────────
  if (resetToken) {
    return (
      <div className="auth-container">
        <Auth
          initialResetToken={resetToken}
          onAuthSuccess={(u) => {
            setResetToken(null);
            setUser(u);
          }}
        />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="auth-container">
        <Auth onAuthSuccess={(u) => setUser(u)} />
      </div>
    );
  }

  // Regular users: Chat only — Admin panel is never shown or referenced here
  return (
    <div className="app-chat-layout">
      <Chat user={user} onLogout={handleLogout} />
    </div>
  );
}

export default App;
