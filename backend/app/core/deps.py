"""
app/core/deps.py — Shared FastAPI Dependency Helpers
─────────────────────────────────────────────────────
Houses reusable Depends()-compatible helpers shared across multiple routers.
Import from here to avoid copy-pasting helpers into individual router files.
"""

from typing import Any, Dict
import app.repositories.user_repository as user_repo


async def fetch_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch the profiles row for a JWT-verified user_id.
    Returns at minimum {"id": user_id} if the profile row is missing.
    Never raises — callers should handle missing fields gracefully.
    """
    profile = user_repo.get_profile_by_id(user_id)
    return profile or {"id": user_id}
