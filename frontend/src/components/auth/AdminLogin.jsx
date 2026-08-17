/**
 * src/components/auth/AdminLogin.jsx — Admin Portal Login Component
 */

import { useState } from 'react';
import { Shield, Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import { adminAuthApi } from '../../api/auth';

export default function AdminLogin({ onAdminSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const data = await adminAuthApi(username.trim(), password);
      const token = data.token;
      
      sessionStorage.setItem('campusmind_admin', 'true');
      sessionStorage.setItem('campusmind_admin_token', token);
      sessionStorage.setItem('admin-token', token);
      toast.success('Admin authentication successful.');
      onAdminSuccess(token);
    } catch (err) {
      const errMsg = err.message || 'Invalid admin credentials. Access denied.';
      setError(errMsg);
      toast.error(errMsg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <Card className="auth-card-container">
        <CardHeader className="auth-header-text">
          <div className="auth-logo" style={{ backgroundColor: 'var(--cm-accent)' }}>
            <Shield className="cm-icon-md text-white" />
          </div>
          <CardTitle style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--font-bold)' }}>
            Admin Portal Access
          </CardTitle>
          <CardDescription>
            Restricted area. Please authenticate with administrator credentials.
          </CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <div className="auth-alert-box auth-alert-error">
              <AlertCircle className="cm-icon-md flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form-body">
            <div className="auth-input-group">
              <label className="auth-label">Admin Username</label>
              <Input
                type="text"
                placeholder="Enter admin username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <div className="auth-input-group">
              <label className="auth-label">Password</label>
              <div className="auth-input-wrapper">
                <Lock className="auth-input-icon-left cm-icon-sm" />
                <Input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="auth-input-with-icon-left auth-input-with-icon-right"
                  required
                />
                <button
                  type="button"
                  className="auth-input-icon-right"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                </button>
              </div>
            </div>

            <Button type="submit" isLoading={isLoading} disabled={isLoading} style={{ width: '100%', marginTop: 'var(--space-2)' }}>
              Authenticate Admin
            </Button>
          </form>
        </CardContent>

        <CardFooter className="auth-footer-text">
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--cm-muted)' }}>
            CampusMind v2.0 • Administrator Security Module
          </span>
        </CardFooter>
      </Card>
    </div>
  );
}
