from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship
from ..database import Base


# Predefined colors for participants
PARTICIPANT_COLORS = [
    "#25D366",  # WhatsApp green
    "#34B7F1",  # WhatsApp blue
    "#9C27B0",  # Purple
    "#FF5722",  # Deep orange
    "#00BCD4",  # Cyan
    "#E91E63",  # Pink
    "#3F51B5",  # Indigo
    "#FF9800",  # Orange
    "#009688",  # Teal
    "#795548",  # Brown
    "#607D8B",  # Blue grey
    "#8BC34A",  # Light green
]


class Participant(Base):
    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    phone_number = Column(String(50), nullable=True)
    message_count = Column(Integer, default=0)
    color = Column(String(7), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    conversation = relationship("Conversation", back_populates="participants")
    messages = relationship("Message", back_populates="participant")

    @staticmethod
    def get_color(index: int) -> str:
        """Get a color for a participant based on their index."""
        return PARTICIPANT_COLORS[index % len(PARTICIPANT_COLORS)]
