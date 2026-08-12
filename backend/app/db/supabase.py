"""
app/db/supabase.py — Supabase Database Client Singleton
────────────────────────────────────────────────────────
Initializes the Supabase client using settings from app.core.config.
"""

from supabase import Client, create_client
from app.core.config import settings

# Supabase client instance
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
