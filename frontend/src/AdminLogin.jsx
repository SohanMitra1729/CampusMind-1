import React, { useState } from 'react';
import { Shield, User, Lock, Eye, EyeOff, AlertCircle, ArrowLeft } from 'lucide-react';
import { Button } from './components/ui/Button';
import { Input } from './components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './components/ui/Card';

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
    <div className="auth-wrapper">
      <Card className="auth-card-container">
        <CardHeader className="auth-header-text">
          <div className="auth-logo" style={{ backgroundColor: 'var(--cm-secondary)' }}>
            <Shield className="cm-icon-lg text-[var(--cm-fg)]" />
          </div>
          <CardTitle>Admin Portal</CardTitle>
          <CardDescription>Restricted access — authorized personnel only</CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <div className="auth-alert-box auth-alert-error">
              <AlertCircle className="cm-icon-md" style={{flexShrink: 0}} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form-body">
            <div className="auth-input-group">
              <label className="auth-label" htmlFor="admin-username">Username</label>
              <div className="auth-input-wrapper">
                <User className="cm-icon-sm auth-input-icon-left" />
                <Input
                  id="admin-username"
                  className="auth-input-with-icon-left"
                  type="text"
                  placeholder="Enter admin username"
                  value={username}
                  onChange={(e) => { setUsername(e.target.value); setError(''); }}
                  autoComplete="off"
                  required
                />
              </div>
            </div>

            <div className="auth-input-group">
              <label className="auth-label" htmlFor="admin-password">Password</label>
              <div className="auth-input-wrapper">
                <Lock className="cm-icon-sm auth-input-icon-left" />
                <Input
                  id="admin-password"
                  className="auth-input-with-icon-left auth-input-with-icon-right"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => { setPassword(e.target.value); setError(''); }}
                  required
                />
                <button
                  type="button"
                  className="auth-input-icon-right"
                  onClick={() => setShowPassword(v => !v)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                </button>
              </div>
            </div>

            <Button
              type="submit"
              style={{width: '100%', marginTop: 'var(--space-2)'}}
              disabled={isLoading || !username.trim() || !password}
              isLoading={isLoading}
            >
              Access Admin Panel
            </Button>
          </form>
        </CardContent>

        <CardFooter>
          <div className="auth-footer-text" style={{width: '100%', display: 'flex', justifyContent: 'center'}}>
            <button
              type="button"
              className="auth-link"
              style={{display: 'flex', alignItems: 'center', gap: 'var(--space-2)'}}
              onClick={() => {
                window.history.replaceState(null, null, window.location.pathname);
                window.location.reload();
              }}
            >
              <ArrowLeft className="cm-icon-sm" /> Back to CampusMind
            </button>
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
