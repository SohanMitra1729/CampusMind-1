"""
app/schemas/notice.py — Notice Request/Response Schemas
"""

from pydantic import BaseModel


class NoticeRequest(BaseModel):
    title: str
    content: str
