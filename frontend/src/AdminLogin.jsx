import { useState } from 'react';

const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'admin123';

export default function AdminLogin({ onAdminSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    // Simulate a brief delay for UX polish
    setTimeout(() => {
      if (username.trim() === ADMIN_USERNAME && password === ADMIN_PASSWORD) {
        // Store admin session in sessionStorage (cleared on browser close)
        sessionStorage.setItem('campusmind_admin', 'true');
        onAdminSuccess();
      } else {
        setError('Invalid admin credentials. Access denied.');
      }
      setIsLoading(false);
    }, 600);
  };

  return (
    <div className="admin-login-overlay">
      <div className="admin-login-card">
        {/* Shield icon header */}
        <div className="admin-login-icon-wrap">
          <div className="admin-login-shield">🛡️</div>
        </div>

        <div className="admin-login-header">
          <h2>Admin Portal</h2>
          <p className="admin-login-subtitle">Restricted access — authorised personnel only</p>
        </div>

        {error && (
          <div className="admin-login-alert">
            <span>⚠️</span> {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="admin-login-form">
          <div className="admin-form-group">
            <label htmlFor="admin-username">Username</label>
            <input
              id="admin-username"
              type="text"
              placeholder="Enter admin username"
              value={username}
              onChange={(e) => { setUsername(e.target.value); setError(''); }}
              autoComplete="off"
              required
            />
          </div>

          <div className="admin-form-group">
            <label htmlFor="admin-password">Password</label>
            <div className="admin-password-wrap">
              <input
                id="admin-password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(''); }}
                required
              />
              <button
                type="button"
                className="admin-toggle-pw"
                onClick={() => setShowPassword(v => !v)}
                tabIndex={-1}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="admin-login-submit-btn"
            disabled={isLoading || !username.trim() || !password}
          >
            {isLoading ? (
              <span className="admin-btn-loading">
                <span className="admin-spinner" /> Verifying…
              </span>
            ) : (
              'Access Admin Panel'
            )}
          </button>
        </form>

        <div className="admin-login-back">
          <button
            type="button"
            className="admin-back-link"
            onClick={() => {
              window.history.replaceState(null, null, window.location.pathname);
              window.location.reload();
            }}
          >
            ← Back to CampusMind
          </button>
        </div>
      </div>
    </div>
  );
}
