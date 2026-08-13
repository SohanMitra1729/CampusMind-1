/**
 * src/pages/AdminLoginPage.jsx — Container Page for Admin Login
 */

import AdminLogin from '../components/auth/AdminLogin';

export default function AdminLoginPage({ onAdminSuccess }) {
  return (
    <div className="auth-container">
      <AdminLogin onAdminSuccess={onAdminSuccess} />
    </div>
  );
}
