"""
security.py — Compatibility module forwarding to app.core.security
"""
from app.core.security import (
    get_current_user,
    get_current_user_optional,
    require_admin,
)

__all__ = ["get_current_user", "get_current_user_optional", "require_admin"]
