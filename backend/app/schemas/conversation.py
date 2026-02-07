from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .participant import ParticipantResponse


class ConversationBase(BaseModel):
    name: str
    is_group: bool = False


class ConversationCreate(ConversationBase):
    pass


class ConversationUpdate(BaseModel):
    name: Optional[str] = None


class ConversationResponse(ConversationBase):
    id: int
    share_token: Optional[str] = None
    message_count: int
    first_message_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    created_at: datetime
    participants: list[ParticipantResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    page: int
    per_page: int
    pages: int
