import React, { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, User, Hash, AlertCircle, CheckCircle2 } from 'lucide-react';
import { Button } from './components/ui/Button';
import { Input } from './components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './components/ui/Card';

export default function Auth({ onAuthSuccess, initialResetToken = null }) {
  const [view, setView] = useState(initialResetToken ? 'reset-password' : 'login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [name, setName] = useState('');
  const [scholarId, setScholarId] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const clearMessage = () => setMessage({ type: '', text: '' });

  const handleSignIn = async (e) => {
    e.preventDefault();
    if (!identifier.trim() || !password.trim()) return;

    setIsLoading(true);
    clearMessage();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to login');
      }

      localStorage.setItem('campusmind_session', JSON.stringify(data.session));
      localStorage.setItem('campusmind_user', JSON.stringify(data.user));
      
      setMessage({ type: 'success', text: 'Login successful!' });
      setTimeout(() => {
        onAuthSuccess(data.user);
      }, 1000);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    if (!name.trim() || !email.trim() || !username.trim() || !scholarId.trim() || !password.trim()) {
      setMessage({ type: 'error', text: 'All fields are required.' });
      return;
    }

    if (!/^\d{7}$/.test(scholarId)) {
      setMessage({ type: 'error', text: 'Scholar ID must be exactly 7 digits.' });
      return;
    }

    setIsLoading(true);
    clearMessage();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, username, scholar_id: scholarId, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to sign up');
      }

      setMessage({ type: 'success', text: data.message || 'Signup successful! Please check your email.' });
      setName('');
      setEmail('');
      setUsername('');
      setScholarId('');
      setPassword('');
      setTimeout(() => setView('login'), 3000);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    if (!identifier.trim()) return;

    setIsLoading(true);
    clearMessage();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Request failed');
      }

      setMessage({ type: 'success', text: data.message });
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!password.trim()) {
      setMessage({ type: 'error', text: 'Password cannot be empty.' });
      return;
    }
    if (password !== confirmPassword) {
      setMessage({ type: 'error', text: 'Passwords do not match.' });
      return;
    }

    setIsLoading(true);
    clearMessage();

    try {
      const response = await fetch('http://127.0.0.1:8000/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ access_token: initialResetToken, password }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Reset failed');
      }

      setMessage({ type: 'success', text: 'Password reset successful! Redirecting to login...' });
      setTimeout(() => {
        window.history.replaceState(null, null, ' ');
        setView('login');
      }, 2000);
    } catch (error) {
      setMessage({ type: 'error', text: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const switchView = (newView) => {
    setView(newView);
    clearMessage();
    setPassword('');
    setConfirmPassword('');
  };

  return (
    <div className="auth-wrapper">
      <Card className="auth-card-container">
        <CardHeader className="auth-header-text">
          <div className="auth-logo">
            <span>CM</span>
          </div>
          <CardTitle>
            {view === 'login' && 'Welcome back'}
            {view === 'signup' && 'Create an account'}
            {view === 'forgot-password' && 'Reset password'}
            {view === 'reset-password' && 'New password'}
          </CardTitle>
          <CardDescription>
            {view === 'login' && 'Enter your credentials to access your account'}
            {view === 'signup' && 'Enter your details to create your CampusMind account'}
            {view === 'forgot-password' && 'Enter your email or username to receive a reset link'}
            {view === 'reset-password' && 'Enter your new password below'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          {message.text && (
            <div className={`auth-alert-box ${message.type === 'error' ? 'auth-alert-error' : 'auth-alert-success'}`}>
              {message.type === 'error' ? <AlertCircle className="cm-icon-md" style={{flexShrink: 0}} /> : <CheckCircle2 className="cm-icon-md" style={{flexShrink: 0}} />}
              <span>{message.text}</span>
            </div>
          )}

          {view === 'login' && (
            <form onSubmit={handleSignIn} className="auth-form-body">
              <div className="auth-input-group">
                <label className="auth-label">Email or Username</label>
                <div className="auth-input-wrapper">
                  <Mail className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left"
                    type="text"
                    placeholder="name@example.com"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="auth-input-group">
                <div className="auth-label-row">
                  <label className="auth-label">Password</label>
                  <button type="button" onClick={() => switchView('forgot-password')} className="auth-link" style={{fontSize: 'var(--text-xs)'}}>
                    Forgot password?
                  </button>
                </div>
                <div className="auth-input-wrapper">
                  <Lock className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left auth-input-with-icon-right"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="auth-input-icon-right"
                  >
                    {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                  </button>
                </div>
              </div>
              <Button type="submit" style={{width: '100%', marginTop: 'var(--space-2)'}} isLoading={isLoading}>
                Sign In
              </Button>
            </form>
          )}

          {view === 'signup' && (
            <form onSubmit={handleSignUp} className="auth-form-body">
              <div className="auth-grid-2">
                <div className="auth-input-group">
                  <label className="auth-label">Full Name</label>
                  <Input
                    type="text"
                    placeholder="John Doe"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    required
                  />
                </div>
                <div className="auth-input-group">
                  <label className="auth-label">Username</label>
                  <Input
                    type="text"
                    placeholder="johndoe"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="auth-input-group">
                <label className="auth-label">Email Address</label>
                <div className="auth-input-wrapper">
                  <Mail className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left"
                    type="email"
                    placeholder="name@university.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="auth-input-group">
                <label className="auth-label">Scholar ID</label>
                <div className="auth-input-wrapper">
                  <Hash className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left"
                    type="text"
                    placeholder="1234567"
                    maxLength={7}
                    value={scholarId}
                    onChange={(e) => setScholarId(e.target.value.replace(/\D/g, ''))}
                    required
                  />
                </div>
              </div>
              <div className="auth-input-group">
                <label className="auth-label">Password</label>
                <div className="auth-input-wrapper">
                  <Lock className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left auth-input-with-icon-right"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="auth-input-icon-right"
                  >
                    {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                  </button>
                </div>
              </div>
              <Button type="submit" style={{width: '100%', marginTop: 'var(--space-2)'}} isLoading={isLoading}>
                Create Account
              </Button>
            </form>
          )}

          {view === 'forgot-password' && (
            <form onSubmit={handleForgotPassword} className="auth-form-body">
              <div className="auth-input-group">
                <label className="auth-label">Email or Username</label>
                <div className="auth-input-wrapper">
                  <Mail className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left"
                    type="text"
                    placeholder="name@example.com"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    required
                  />
                </div>
              </div>
              <Button type="submit" style={{width: '100%', marginTop: 'var(--space-2)'}} isLoading={isLoading}>
                Send Reset Link
              </Button>
            </form>
          )}

          {view === 'reset-password' && (
            <form onSubmit={handleResetPassword} className="auth-form-body">
              <div className="auth-input-group">
                <label className="auth-label">New Password</label>
                <div className="auth-input-wrapper">
                  <Lock className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left auth-input-with-icon-right"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="auth-input-icon-right"
                  >
                    {showPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                  </button>
                </div>
              </div>
              <div className="auth-input-group">
                <label className="auth-label">Confirm Password</label>
                <div className="auth-input-wrapper">
                  <Lock className="cm-icon-sm auth-input-icon-left" />
                  <Input
                    className="auth-input-with-icon-left auth-input-with-icon-right"
                    type={showConfirmPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="auth-input-icon-right"
                  >
                    {showConfirmPassword ? <EyeOff className="cm-icon-sm" /> : <Eye className="cm-icon-sm" />}
                  </button>
                </div>
              </div>
              <Button type="submit" style={{width: '100%', marginTop: 'var(--space-2)'}} isLoading={isLoading}>
                Reset Password
              </Button>
            </form>
          )}
        </CardContent>

        <CardFooter>
          <div className="auth-footer-text" style={{width: '100%'}}>
            {view === 'login' && (
              <>
                Don't have an account?{' '}
                <button onClick={() => switchView('signup')} className="auth-link">
                  Sign up
                </button>
              </>
            )}
            {view === 'signup' && (
              <>
                Already have an account?{' '}
                <button onClick={() => switchView('login')} className="auth-link">
                  Sign in
                </button>
              </>
            )}
            {view === 'forgot-password' && (
              <>
                Remember your password?{' '}
                <button onClick={() => switchView('login')} className="auth-link">
                  Sign in
                </button>
              </>
            )}
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}
