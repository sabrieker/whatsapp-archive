from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    status = Column(String(50), default="pending")  # pending, uploading, processing, completed, failed
    filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Progress tracking
    total_chunks = Column(Integer, default=0)
    uploaded_chunks = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    processed_messages = Column(Integer, default=0)
    total_media = Column(Integer, default=0)
    processed_media = Column(Integer, default=0)

    # Error tracking
    error_message = Column(Text, nullable=True)

    # Storage
    temp_storage_key = Column(String(512), nullable=True)  # Temporary storage in MinIO

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="import_jobs")
