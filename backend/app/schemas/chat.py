"""
app/schemas/chat.py — Chat Request/Response Schemas
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    query: str
    metadata_filter: Optional[Dict[str, Any]] = None
    chat_id: Optional[str] = None
