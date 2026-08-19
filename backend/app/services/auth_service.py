"""
app/services/auth_service.py — Authentication Business Logic
─────────────────────────────────────────────────────────────
Encapsulates all Supabase Auth operations (sign-up, login, password reset).
Routes in main.py call these functions; they never touch supabase.auth directly.

Why a service?
  Repository  = "talk to the DB table"
  Service     = "do the business action" (which may call auth + repo + validation)
"""

import re
from app.db.supabase import supabase
from app.core.config import settings
import app.repositories.user_repository as user_repo


# ── Sign Up ───────────────────────────────────────────────────────────────────

def sign_up(email: str, password: str, name: str, username: str, scholar_id: str) -> dict:
    """
    Register a new student account via Supabase Auth.
    - Validates scholar_id, username, email before calling Supabase.
    - Checks for existing duplicates in the profiles table to avoid trigger failures.
    - Handles Supabase/PostgreSQL duplicate key errors gracefully.

    Returns:
        {"message": str}   on success
    Raises:
        ValueError          for validation or duplicate errors
        Exception           for unexpected Supabase/network errors
    """
    email = email.strip().lower()
    username = username.strip().lower()
    scholar_id = scholar_id.strip()
    name = name.strip()

    if not email or "@" not in email:
        raise ValueError("Please enter a valid email address.")
    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    if not re.match(r"^\d{7}$", scholar_id):
        raise ValueError("Scholar ID must be exactly 7 digits.")
    if len(username) < 3:
        raise ValueError("Username must be at least 3 characters.")
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValueError("Username can only contain letters, numbers, and underscores.")

    # 1. Pre-flight check against profiles table
    if user_repo.check_username_exists(username):
        raise ValueError(f"Username '@{username}' is already taken. Please choose another username.")

    if user_repo.check_scholar_id_exists(scholar_id):
        raise ValueError(f"Scholar ID '{scholar_id}' is already registered. Please login or reset your password.")

    if user_repo.check_email_exists(email):
        raise ValueError(f"An account with email '{email}' is already registered. Please login.")

    # 2. Call Supabase Auth
    try:
        res = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name":       name,
                    "username":   username,
                    "scholar_id": scholar_id,
                }
            },
        })
    except Exception as e:
        err_msg = str(e).lower()
        if "database error saving new user" in err_msg or "unique constraint" in err_msg or "duplicate key" in err_msg:
            raise ValueError("An account with this username, email, or Scholar ID already exists. Please login instead.")
        if "already registered" in err_msg or "user already exists" in err_msg:
            raise ValueError(f"An account with email '{email}' is already registered. Please login.")
        if "rate limit" in err_msg or "security purposes" in err_msg:
            raise ValueError("Too many signup attempts. Please wait a few seconds before trying again.")
        raise ValueError(str(e))

    if not res.user:
        raise ValueError("Signup failed. Please try again.")

    return {"message": "Sign up successful! Please check your email for confirmation."}


# ── Login ─────────────────────────────────────────────────────────────────────

def login(identifier: str, password: str) -> dict:
    """
    Authenticate a student using either email or username.
    - If no '@' in identifier → treats it as a username and resolves to email
      via user_repository before calling Supabase Auth.
    - Returns session tokens + user profile fields.

    Returns:
        {
            "session": { access_token, refresh_token, expires_at },
            "user":    { id, email, name, username, scholar_id }
        }
    Raises:
        ValueError   for unknown username
        Exception    for wrong password / Supabase errors (re-raised to route)
    """
    email = identifier

    # Username login: resolve to email first
    if "@" not in identifier:
        resolved = user_repo.get_email_by_username(identifier)
        if not resolved:
            raise ValueError("Username not found.")
        email = resolved

    res = supabase.auth.sign_in_with_password({"email": email, "password": password})

    profile = user_repo.get_profile_by_id(str(res.user.id)) or {}

    return {
        "session": {
            "access_token":  res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "expires_at":    res.session.expires_at,
        },
        "user": {
            "id":         res.user.id,
            "email":      res.user.email,
            "name":       profile.get("name"),
            "username":   profile.get("username"),
            "scholar_id": profile.get("scholar_id"),
        },
    }


# ── Forgot Password ───────────────────────────────────────────────────────────

def forgot_password(identifier: str) -> dict:
    """
    Trigger a Supabase password-reset email.
    - Accepts either email or username.
    - Redirects to FRONTEND_URL after reset.

    Returns:
        {"message": str}
    Raises:
        ValueError   for unknown username
        Exception    for Supabase errors (re-raised to route)
    """
    email = identifier

    if "@" not in identifier:
        resolved = user_repo.get_email_by_username(identifier)
        if not resolved:
            raise ValueError("Username not found.")
        email = resolved

    supabase.auth.reset_password_for_email(email, {"redirect_to": settings.FRONTEND_URL})

    return {"message": "Password reset email sent. Please check your inbox."}


# ── Reset Password ────────────────────────────────────────────────────────────

def reset_password(access_token: str, new_password: str) -> dict:
    """
    Complete a password reset using the one-time access_token from the reset email.
    - Validates the token via supabase.auth.get_user().
    - Uses the admin SDK to update the password (bypasses the need to be logged in).

    Returns:
        {"message": str}
    Raises:
        ValueError    if token is invalid/expired
        Exception     for Supabase errors (re-raised to route)
    """
    user_response = supabase.auth.get_user(access_token)

    if not user_response or not user_response.user:
        raise ValueError("Invalid or expired reset token.")

    supabase.auth.admin.update_user_by_id(
        user_response.user.id,
        {"password": new_password},
    )

    return {"message": "Password has been reset successfully."}
