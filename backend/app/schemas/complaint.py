"""
app/schemas/complaint.py — Complaint Request/Response Schemas
"""

from typing import Optional
from pydantic import BaseModel


class ComplaintClassifyRequest(BaseModel):
    text: str


class ComplaintRequest(BaseModel):
    text: str
    hostel_id: Optional[str] = None
    room_number: Optional[str] = None


class ComplaintStatusRequest(BaseModel):
    status: str  # open | in_progress | resolved | dismissed
