from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class MediaBase(BaseModel):
    media_type: str
    mime_type: Optional[str] = None
    original_filename: Optional[str] = None


class MediaResponse(MediaBase):
    id: int
    message_id: int
    storage_key: str
    file_size: Optional[int] = None
    thumbnail_key: Optional[str] = None
    url: Optional[str] = None  # Generated presigned URL
    thumbnail_url: Optional[str] = None

    class Config:
        from_attributes = True
