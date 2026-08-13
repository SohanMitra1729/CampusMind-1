/**
 * src/pages/AuthPage.jsx — Container Page for Student Auth
 */

import Auth from '../components/auth/Auth';

export default function AuthPage({ onAuthSuccess }) {
  return (
    <div className="auth-container">
      <Auth onAuthSuccess={onAuthSuccess} />
    </div>
  );
}
