from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from .media import MediaResponse


class MessageBase(BaseModel):
    sender_name: str
    content: Optional[str] = None
    message_type: str = "text"


class MessageResponse(MessageBase):
    id: int
    conversation_id: int
    participant_id: Optional[int] = None
    timestamp: datetime
    has_media: bool
    media_files: list[MediaResponse] = []
    participant_color: Optional[str] = None

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    page: int
    per_page: int
    pages: int
    has_more: bool
