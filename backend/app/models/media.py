from sqlalchemy import Column, Integer, String, BigInteger, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True)
    storage_key = Column(String(512), nullable=False)  # MinIO object key
    original_filename = Column(String(255), nullable=True)
    media_type = Column(String(50), nullable=False)  # image, video, audio, document
    mime_type = Column(String(100), nullable=True)
    file_size = Column(BigInteger, nullable=True)
    thumbnail_key = Column(String(512), nullable=True)  # MinIO key for thumbnail
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    message = relationship("Message", back_populates="media_files")
