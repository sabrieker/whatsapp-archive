from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional
from ..models import Message, Conversation, Participant
import logging

logger = logging.getLogger(__name__)


class SearchService:
    """Full-text search service for messages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_messages(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> dict:
        """Search messages using PostgreSQL full-text search or ILIKE fallback."""
        offset = (page - 1) * per_page

        # Use ILIKE for better multilingual support (Turkish, etc.)
        search_pattern = f"%{query}%"

        # Base query with eager loading
        stmt = (
            select(Message)
            .options(
                selectinload(Message.participant),
                selectinload(Message.media_files),
            )
            .where(Message.content.ilike(search_pattern))
        )

        # Filter by conversation if specified
        if conversation_id:
            stmt = stmt.where(Message.conversation_id == conversation_id)

        # Count total matches
        count_stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.content.ilike(search_pattern))
        )
        if conversation_id:
            count_stmt = count_stmt.where(Message.conversation_id == conversation_id)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Get results ordered by timestamp desc
        stmt = stmt.order_by(Message.timestamp.desc()).offset(offset).limit(per_page)

        result = await self.db.execute(stmt)
        messages = result.scalars().all()

        return {
            "items": messages,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
            "query": query,
        }

    async def update_search_vector(self, message: Message):
        """Update the search vector for a message."""
        if message.content:
            # Use raw SQL for tsvector update
            await self.db.execute(
                text("""
                    UPDATE messages
                    SET search_vector = to_tsvector('english', :content)
                    WHERE id = :id
                """),
                {"content": message.content, "id": message.id},
            )
            await self.db.commit()

    async def bulk_update_search_vectors(self, conversation_id: int):
        """Update search vectors for all messages in a conversation."""
        await self.db.execute(
            text("""
                UPDATE messages
                SET search_vector = to_tsvector('english', COALESCE(content, ''))
                WHERE conversation_id = :conversation_id
            """),
            {"conversation_id": conversation_id},
        )
        await self.db.commit()
        logger.info(f"Updated search vectors for conversation {conversation_id}")

    async def search_conversations(
        self,
        query: str,
        page: int = 1,
        per_page: int = 20,
    ) -> dict:
        """Search for conversations by name."""
        offset = (page - 1) * per_page

        # Simple ILIKE search for conversation names
        stmt = (
            select(Conversation)
            .where(Conversation.name.ilike(f"%{query}%"))
            .order_by(Conversation.last_message_at.desc())
            .offset(offset)
            .limit(per_page)
        )

        # Count total
        count_stmt = (
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.name.ilike(f"%{query}%"))
        )

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        result = await self.db.execute(stmt)
        conversations = result.scalars().all()

        return {
            "items": conversations,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page if total > 0 else 0,
        }

    async def get_message_context(
        self,
        message_id: int,
        context_size: int = 5,
    ) -> dict:
        """Get messages around a specific message for context."""
        # Get the target message
        target = await self.db.get(Message, message_id)
        if not target:
            return {"before": [], "target": None, "after": []}

        # Get messages before
        before_stmt = (
            select(Message)
            .where(Message.conversation_id == target.conversation_id)
            .where(Message.timestamp < target.timestamp)
            .order_by(Message.timestamp.desc())
            .limit(context_size)
        )
        before_result = await self.db.execute(before_stmt)
        before = list(reversed(before_result.scalars().all()))

        # Get messages after
        after_stmt = (
            select(Message)
            .where(Message.conversation_id == target.conversation_id)
            .where(Message.timestamp > target.timestamp)
            .order_by(Message.timestamp.asc())
            .limit(context_size)
        )
        after_result = await self.db.execute(after_stmt)
        after = list(after_result.scalars().all())

        return {
            "before": before,
            "target": target,
            "after": after,
        }
