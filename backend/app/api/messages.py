from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime

from ..database import get_db
from ..models import Message, Participant
from ..schemas import MessageResponse, MessageListResponse
from ..services.storage import StorageService

router = APIRouter()


def enrich_message_response(message: Message, storage: StorageService) -> MessageResponse:
    """Enrich message with participant color and media URLs."""
    response = MessageResponse.model_validate(message)

    # Add participant color
    if message.participant:
        response.participant_color = message.participant.color

    # Add media URLs
    for media in response.media_files:
        media.url = storage.get_presigned_url(media.storage_key)
        if media.thumbnail_key:
            media.thumbnail_url = storage.get_presigned_url(media.thumbnail_key)

    return response


@router.get("/conversation/{conversation_id}", response_model=MessageListResponse)
async def get_messages(
    conversation_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    before: Optional[datetime] = None,
    after: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get paginated messages for a conversation."""
    offset = (page - 1) * per_page

    # Base query
    stmt = (
        select(Message)
        .options(
            selectinload(Message.participant),
            selectinload(Message.media_files),
        )
        .where(Message.conversation_id == conversation_id)
    )

    # Time filters
    if before:
        stmt = stmt.where(Message.timestamp < before)
    if after:
        stmt = stmt.where(Message.timestamp > after)

    # Count total
    count_stmt = select(func.count()).select_from(Message).where(Message.conversation_id == conversation_id)
    if before:
        count_stmt = count_stmt.where(Message.timestamp < before)
    if after:
        count_stmt = count_stmt.where(Message.timestamp > after)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get paginated results - newest first (DESC)
    stmt = stmt.order_by(Message.timestamp.desc())
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Enrich responses
    storage = StorageService()
    enriched = [enrich_message_response(m, storage) for m in messages]

    pages = (total + per_page - 1) // per_page if total > 0 else 0

    return MessageListResponse(
        items=enriched,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_more=page < pages,
    )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single message by ID."""
    stmt = (
        select(Message)
        .options(
            selectinload(Message.participant),
            selectinload(Message.media_files),
        )
        .where(Message.id == message_id)
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    storage = StorageService()
    return enrich_message_response(message, storage)


@router.get("/{message_id}/context")
async def get_message_context(
    message_id: int,
    context_size: int = Query(5, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get messages around a specific message for context."""
    from ..services.search import SearchService

    search_service = SearchService(db)
    context = await search_service.get_message_context(message_id, context_size)

    if not context["target"]:
        raise HTTPException(status_code=404, detail="Message not found")

    storage = StorageService()

    return {
        "before": [enrich_message_response(m, storage) for m in context["before"]],
        "target": enrich_message_response(context["target"], storage),
        "after": [enrich_message_response(m, storage) for m in context["after"]],
    }
