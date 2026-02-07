from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ParticipantBase(BaseModel):
    name: str
    phone_number: Optional[str] = None


class ParticipantResponse(ParticipantBase):
    id: int
    conversation_id: int
    message_count: int
    color: str
    created_at: datetime

    class Config:
        from_attributes = True
