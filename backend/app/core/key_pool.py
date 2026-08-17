"""
app/core/key_pool.py — Multi-Key Load Balancing & Automatic 429/401 Failover Pool
─────────────────────────────────────────────────────────────────────────────────
Manages pools of Google Gemini (embeddings) and Groq (completions) API keys
with automatic instant failover on Rate Limits (429), Invalid/Unauthorized keys (401),
Resource Exhaustion (403), or Token-Per-Minute (TPM) Quota limits.
"""

import time
import httpx
from typing import List, Dict, Any, Optional, AsyncGenerator
from groq import Groq, AsyncGroq
from app.core.config import settings
from app.core.logger import logger


class GeminiKeyPool:
    """Automatic 429 / 401 failover pool for Google Gemini Embeddings API."""
    def __init__(self):
        self._current_idx = 0

    @property
    def keys(self) -> List[str]:
        return settings.google_keys

    def get_current_key(self) -> str:
        keys = self.keys
        if not keys:
            return ""
        return keys[self._current_idx % len(keys)]

    def rotate_key(self) -> str:
        keys = self.keys
        if len(keys) > 1:
            self._current_idx = (self._current_idx + 1) % len(keys)
            logger.warning(
                f"[GeminiKeyPool] Rotated to key index {self._current_idx + 1}/{len(keys)}"
            )
        return self.get_current_key()

    def get_embedding(self, text: str, max_retries_per_key: int = 2) -> List[float]:
        keys = self.keys
        total_attempts = max(len(keys) * max_retries_per_key, 1)
        last_err = None

        for attempt in range(total_attempts):
            api_key = self.get_current_key()
            if not api_key:
                raise RuntimeError("[GeminiKeyPool] No Google Gemini API key configured.")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={api_key}"
            payload = {
                "model": "models/gemini-embedding-2",
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": 1536
            }
            try:
                with httpx.Client(timeout=20.0) as client:
                    resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if resp.status_code in (401, 403, 429) or "RESOURCE_EXHAUSTED" in resp.text:
                        logger.warning(
                            f"[GeminiKeyPool] Key index {self._current_idx + 1} returned status {resp.status_code}. Rotating..."
                        )
                        self.rotate_key()
                        time.sleep(0.5)
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["embedding"]["values"]
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                if any(x in err_msg for x in ["401", "403", "429", "unauthorized", "resource_exhausted", "quota"]):
                    logger.warning(f"[GeminiKeyPool] Error with key index {self._current_idx + 1} ({e}). Rotating...")
                    self.rotate_key()
                    time.sleep(0.5)
                else:
                    raise e
        raise RuntimeError(f"[GeminiKeyPool] All {len(keys)} Gemini keys failed: {last_err}")

    async def get_embedding_async(self, text: str, max_retries_per_key: int = 2) -> List[float]:
        keys = self.keys
        total_attempts = max(len(keys) * max_retries_per_key, 1)
        last_err = None

        for attempt in range(total_attempts):
            api_key = self.get_current_key()
            if not api_key:
                raise RuntimeError("[GeminiKeyPool] No Google Gemini API key configured.")

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent?key={api_key}"
            payload = {
                "model": "models/gemini-embedding-2",
                "content": {"parts": [{"text": text}]},
                "outputDimensionality": 1536
            }
            try:
                async with httpx.AsyncClient(timeout=20.0) as client:
                    resp = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                    if resp.status_code in (401, 403, 429) or "RESOURCE_EXHAUSTED" in resp.text:
                        logger.warning(
                            f"[GeminiKeyPool] Async Key index {self._current_idx + 1} returned status {resp.status_code}. Rotating..."
                        )
                        self.rotate_key()
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["embedding"]["values"]
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                if any(x in err_msg for x in ["401", "403", "429", "unauthorized", "resource_exhausted", "quota"]):
                    logger.warning(f"[GeminiKeyPool] Async error with key index {self._current_idx + 1} ({e}). Rotating...")
                    self.rotate_key()
                else:
                    raise e
        raise RuntimeError(f"[GeminiKeyPool] All {len(keys)} Gemini keys failed: {last_err}")


class GroqKeyPool:
    """Automatic 429 / 401 failover pool for Groq chat completions."""
    def __init__(self):
        self._current_idx = 0

    @property
    def keys(self) -> List[str]:
        return settings.groq_keys

    def get_current_client(self) -> Groq:
        keys = self.keys
        key = keys[self._current_idx % len(keys)] if keys else ""
        return Groq(api_key=key or "placeholder_key")

    def get_current_async_client(self) -> AsyncGroq:
        keys = self.keys
        key = keys[self._current_idx % len(keys)] if keys else ""
        return AsyncGroq(api_key=key or "placeholder_key")

    def rotate_key(self) -> None:
        keys = self.keys
        if len(keys) > 1:
            self._current_idx = (self._current_idx + 1) % len(keys)
            logger.warning(
                f"[GroqKeyPool] Rotated to key index {self._current_idx + 1}/{len(keys)}"
            )

    def chat_completion(self, **kwargs) -> Any:
        keys = self.keys
        total_attempts = max(len(keys), 1)
        last_err = None

        for _ in range(total_attempts):
            client = self.get_current_client()
            try:
                return client.chat.completions.create(**kwargs)
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                if any(x in err_msg for x in ["401", "429", "rate limit", "tpm", "invalid_api_key", "invalid api key"]):
                    logger.warning(f"[GroqKeyPool] Key index {self._current_idx + 1} error ({e}). Rotating...")
                    self.rotate_key()
                else:
                    raise e
        raise last_err

    async def async_chat_completion_stream(self, **kwargs) -> AsyncGenerator:
        keys = self.keys
        total_attempts = max(len(keys), 1)
        last_err = None

        for _ in range(total_attempts):
            client = self.get_current_async_client()
            try:
                stream = await client.chat.completions.create(stream=True, **kwargs)
                async for chunk in stream:
                    yield chunk
                return
            except Exception as e:
                last_err = e
                err_msg = str(e).lower()
                if any(x in err_msg for x in ["401", "429", "rate limit", "tpm", "invalid_api_key", "invalid api key"]):
                    logger.warning(f"[GroqKeyPool] Async Stream Key index {self._current_idx + 1} error ({e}). Rotating...")
                    self.rotate_key()
                else:
                    raise e
        raise last_err


# Global singleton key pools
gemini_pool = GeminiKeyPool()
groq_pool = GroqKeyPool()
