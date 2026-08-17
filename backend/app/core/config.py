"""
app/core/config.py — Centralized Configuration Management
────────────────────────────────────────────────────────
Loads and type-checks environment variables strictly from backend/.env.
"""

from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to backend/.env (config.py -> core -> app -> backend -> .env)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # ── Database & External APIs ─────────────────────────────────────────────
    SUPABASE_URL: str
    SUPABASE_SERVICE_KEY: str
    GROQ_API_KEY: str
    GROQ_MODEL: str
    GOOGLE_API_KEY: str

    # Optional Multi-Key Rotation Pools (comma-separated: key1,key2,key3)
    GROQ_API_KEYS: Optional[str] = None
    GOOGLE_API_KEYS: Optional[str] = None

    # ── Admin Auth ───────────────────────────────────────────────────────────
    ADMIN_USERNAME: str
    ADMIN_SECRET: str

    # ── Frontend & Server ───────────────────────────────────────────────────
    FRONTEND_URL: str

    # ── Telegram Bots (Optional) ─────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None
    STAFF_BOT_TOKEN: Optional[str] = None
    STAFF_BOT_WEBHOOK_URL: Optional[str] = None

    @property
    def groq_keys(self) -> list[str]:
        keys = []
        if self.GROQ_API_KEYS:
            keys.extend([k.strip() for k in self.GROQ_API_KEYS.split(",") if k.strip()])
        if self.GROQ_API_KEY and self.GROQ_API_KEY.strip() not in keys:
            keys.append(self.GROQ_API_KEY.strip())
        return keys or [self.GROQ_API_KEY or ""]

    @property
    def google_keys(self) -> list[str]:
        keys = []
        if self.GOOGLE_API_KEYS:
            keys.extend([k.strip() for k in self.GOOGLE_API_KEYS.split(",") if k.strip()])
        if self.GOOGLE_API_KEY and self.GOOGLE_API_KEY.strip() not in keys:
            keys.append(self.GOOGLE_API_KEY.strip())
        return keys or [self.GOOGLE_API_KEY or ""]

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global singleton settings instance
settings = Settings()
