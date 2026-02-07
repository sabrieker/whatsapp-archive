from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Conversation, Message
from ..schemas import ConversationResponse, MessageResponse, MessageListResponse
from ..services.storage import StorageService

router = APIRouter()


async def get_shared_conversation(token: str, db: AsyncSession) -> Conversation:
    """Get a conversation by share token."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.participants))
        .where(Conversation.share_token == token)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Shared conversation not found")

    return conversation


@router.get("/{token}", response_model=ConversationResponse)
async def get_shared_conversation_info(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get shared conversation info."""
    conversation = await get_shared_conversation(token, db)

    # Don't expose the share token in response
    response = ConversationResponse.model_validate(conversation)
    response.share_token = None

    return response


@router.get("/{token}/messages", response_model=MessageListResponse)
async def get_shared_messages(
    token: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get messages from a shared conversation."""
    conversation = await get_shared_conversation(token, db)

    from sqlalchemy import func

    offset = (page - 1) * per_page

    # Count total
    count_stmt = select(func.count()).select_from(Message).where(Message.conversation_id == conversation.id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get messages - newest first (DESC)
    stmt = (
        select(Message)
        .options(
            selectinload(Message.participant),
            selectinload(Message.media_files),
        )
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.timestamp.desc())
        .offset(offset)
        .limit(per_page)
    )

    result = await db.execute(stmt)
    messages = result.scalars().all()

    # Enrich responses
    storage = StorageService()
    enriched = []
    for message in messages:
        response = MessageResponse.model_validate(message)
        if message.participant:
            response.participant_color = message.participant.color
        for media in response.media_files:
            media.url = storage.get_presigned_url(media.storage_key)
        enriched.append(response)

    pages = (total + per_page - 1) // per_page if total > 0 else 0

    return MessageListResponse(
        items=enriched,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
        has_more=page < pages,
    )


@router.get("/{token}/search", response_model=MessageListResponse)
async def search_shared_messages(
    token: str,
    q: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search messages in a shared conversation."""
    conversation = await get_shared_conversation(token, db)

    from ..services.search import SearchService

    search_service = SearchService(db)
    results = await search_service.search_messages(
        query=q,
        conversation_id=conversation.id,
        page=page,
        per_page=per_page,
    )

    # Enrich responses
    storage = StorageService()
    enriched = []
    for message in results["items"]:
        response = MessageResponse.model_validate(message)
        if message.participant:
            response.participant_color = message.participant.color
        enriched.append(response)

    return MessageListResponse(
        items=enriched,
        total=results["total"],
        page=results["page"],
        per_page=results["per_page"],
        pages=results["pages"],
        has_more=results["page"] < results["pages"],
    )
