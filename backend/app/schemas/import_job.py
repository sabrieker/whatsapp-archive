from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ImportJobCreate(BaseModel):
    filename: str
    file_size: int
    total_chunks: int


class ImportJobResponse(BaseModel):
    id: int
    conversation_id: Optional[int] = None
    status: str
    filename: Optional[str] = None
    file_size: Optional[int] = None
    total_chunks: int
    uploaded_chunks: int
    total_messages: int
    processed_messages: int
    total_media: int
    processed_media: int
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ChunkUploadResponse(BaseModel):
    job_id: int
    chunk_number: int
    uploaded_chunks: int
    total_chunks: int
    complete: bool


class ImportStartRequest(BaseModel):
    job_id: int


class ImportProgressResponse(BaseModel):
    job_id: int
    status: str
    progress_percent: float
    total_messages: int
    processed_messages: int
    total_media: int
    processed_media: int
    error_message: Optional[str] = None
