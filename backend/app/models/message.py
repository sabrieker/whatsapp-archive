from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Boolean, Index, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import relationship
from ..database import Base


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    sender_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)
    message_type = Column(String(50), default="text")  # text, image, video, audio, document, sticker, system
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    has_media = Column(Boolean, default=False)
    search_vector = Column(TSVECTOR, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    participant = relationship("Participant", back_populates="messages")
    media_files = relationship("MediaFile", back_populates="message", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_messages_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_messages_conversation_timestamp", "conversation_id", "timestamp"),
    )
