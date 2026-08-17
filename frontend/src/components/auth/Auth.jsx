/**
 * src/components/auth/Auth.jsx — Student Login & Registration Form
 *
 * Uses the useAuth hook for all auth operations so that state is managed
 * centrally in the hook — no direct API calls or manual localStorage writes here.
 */

import { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, Hash, AlertCircle, CheckCircle2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import { useAuth } from '../../hooks/useAuth';

export default function Auth({ onAuthSuccess, initialResetToken = null }) {
  const [view, setView] = useState(initialResetToken ? 'reset-password' : 'login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [scholarId, setScholarId] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localAlert, setLocalAlert] = useState(null);

  const { login, signup, forgotPassword, resetPassword, isLoading } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLocalAlert(null);

    try {
      if (view === 'login') {
        const identifier = email || username;
        const user = await login(identifier, password);
        toast.success(`Welcome back, ${user.name || user.username || 'Student'}!`);
        onAuthSuccess(user);
      } else if (view === 'signup') {
        await signup({ name: name.trim(), username: username.trim(), email: email.trim(), scholar_id: scholarId.trim(), password });
        const successMsg = 'Account created! Check your email to confirm registration before signing in.';
        setLocalAlert({ type: 'success', text: successMsg });
        toast.success(successMsg);
        setView('login');
        setPassword('');
      } else if (view === 'forgot-password') {
        await forgotPassword(email.trim());
        const msg = 'Password reset link sent! Check your inbox.';
        setLocalAlert({ type: 'success', text: msg });
        toast.success(msg);
      } else if (view === 'reset-password') {
        await resetPassword(initialResetToken, password);
        const msg = 'Password updated! Please log in with your new password.';
        setLocalAlert({ type: 'success', text: msg });
        toast.success(msg);
        setView('login');
        setPassword('');
      }
    } catch (err) {
      const errMsg = err.message || 'An unexpected error occurred.';
      setLocalAlert({ type: 'error', text: errMsg });
      toast.error(errMsg);
    }
  };

  const switchView = (newView) => {
    setView(newView);
    setLocalAlert(null);
  };

  return (
    <div className="auth-wrapper">
      <Card className="auth-card-container">
        <CardHeader className="auth-header-text">
          <div className="auth-logo">
            <span>CM</span>
          </div>
          <CardTitle style={{ fontSize: 'var(--text-xl)', fontWeight: 'var(--font-bold)' }}>
            {view === 'login' && 'Welcome back'}
            {view === 'signup' && 'Create an account'}
            {view === 'forgot-password' && 'Reset your password'}
            {view === 'reset-password' && 'Set new password'}
          </CardTitle>
          <CardDescription>
            {view === 'login' && 'Enter your campus credentials to access CampusMind'}
            {view === 'signup' && 'Register with your NIT Silchar scholar details'}
            {view === 'forgot-password' && "We'll send a recovery link to your registered email"}
            {view === 'reset-password' && 'Enter a strong new password for your account'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {localAlert && (
            <div className={`auth-alert-box ${localAlert.type === 'error' ? 'auth-alert-error' : 'auth-alert-success'}`}>
              {localAlert.type === 'error' ? <AlertCircle className="cm-icon-md flex-shrink-0" /> : <CheckCircle2 className="cm-icon-md flex-shrink-0" />}
              <span>{localAlert.text}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="auth-form-body">
            {view === 'signup' && (
              <>
                <div className="auth-input-group">
                  <label className="auth-label">Full Name</label>
                  <Input type="text" placeholder="e.g. Rahul Sharma" value={name} onChange={(e) => setName(e.target.value)} required />
                </div>
                <div className="auth-grid-2">
                  <div className="auth-input-group">
                    <label className="auth-label">Username</label>
                    <Input type="text" placeholder="e.g. rahul_s" value={username} onChange={(e) => setUsername(e.target.value)} required />
                  </div>
                  <div className="auth-input-group">
                    <label className="auth-label">Scholar ID</label>
                    <div className="auth-input-wrapper">
                      <Hash className="auth-input-icon-left cm-icon-sm" />
                      <Input type="text" placeholder="e.g. 2112001" value={scholarId} onChange={(e) => setScholarId(e.target.value)} className="auth-input-with-icon-left" required />
                    </div>
                  </div>
                </div>
              </>
            )}

            {(view === 'login' || view === 'signup' || view === 'forgot-password') && (
              <div className="auth-input-group">
                <label className="auth-label">
                  {view === 'signup' || view === 'forgot-password' ? 'Email Address' : 'Email or Username'}
                </label>
                <div className="auth-input-wrapper">
                  <Mail className="auth-input-icon-left cm-icon-sm" />
                  <Input
                    type={view === 'login' ? 'text' : 'email'}
                    placeholder={view === 'login' ? 'scholar_id@nits.ac.in or username' : 'name@nits.ac.in'}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="auth-input-with-icon-left"
                    required
                  />
                </div>
              </div>
            )}

            {(view === 'login' || view === 'signup' || view === 'reset-password') && (
              <div className="auth-input-group">
                <div className="auth-label-row">
                  <label className="auth-label">Password</label>
                  {view === 'login' && (
                    <button type="button" className="auth-link" onClick={() => switchView('forgot-password')} style={{ fontSize: 'var(--text-xs)' }}>
                      Forgot?
                    </button>
                  )}
                </div>
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
                  <button type="button" className="auth-input-icon-right" onClick={() => setShowPassword(!showPassword)}>
                    {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                  </button>
                </div>
              </div>
            )}

            <Button type="submit" isLoading={isLoading} disabled={isLoading} style={{ width: '100%', marginTop: 'var(--space-2)' }}>
              {view === 'login' && 'Sign In'}
              {view === 'signup' && 'Create Account'}
              {view === 'forgot-password' && 'Send Reset Link'}
              {view === 'reset-password' && 'Update Password'}
            </Button>
          </form>
        </CardContent>

        <CardFooter className="auth-footer-text">
          {view === 'login' && (
            <span>
              Don't have an account?
              <button type="button" className="auth-link" onClick={() => switchView('signup')}>Sign up</button>
            </span>
          )}
          {view === 'signup' && (
            <span>
              Already have an account?
              <button type="button" className="auth-link" onClick={() => switchView('login')}>Sign in</button>
            </span>
          )}
          {(view === 'forgot-password' || view === 'reset-password') && (
            <button type="button" className="auth-link" onClick={() => switchView('login')}>← Back to Sign in</button>
          )}
        </CardFooter>
      </Card>
    </div>
  );
}
