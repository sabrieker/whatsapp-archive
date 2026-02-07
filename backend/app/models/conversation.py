from sqlalchemy import Column, Integer, String, Boolean, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base
import secrets


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    is_group = Column(Boolean, default=False)
    share_token = Column(String(64), unique=True, index=True, nullable=True)
    message_count = Column(Integer, default=0)
    first_message_at = Column(DateTime(timezone=True), nullable=True)
    last_message_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    participants = relationship("Participant", back_populates="conversation", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    import_jobs = relationship("ImportJob", back_populates="conversation", cascade="all, delete-orphan")

    def generate_share_token(self) -> str:
        """Generate a unique share token."""
        self.share_token = secrets.token_urlsafe(32)
        return self.share_token

    def revoke_share_token(self):
        """Revoke the share token."""
        self.share_token = None
