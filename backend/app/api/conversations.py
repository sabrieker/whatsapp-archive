from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional

from ..database import get_db
from ..models import Conversation, Participant
from ..schemas import ConversationResponse, ConversationListResponse, ConversationUpdate

router = APIRouter()


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List all conversations with pagination."""
    offset = (page - 1) * per_page

    # Base query
    stmt = select(Conversation).options(selectinload(Conversation.participants))

    # Search filter
    if search:
        stmt = stmt.where(Conversation.name.ilike(f"%{search}%"))

    # Count total
    count_stmt = select(func.count()).select_from(Conversation)
    if search:
        count_stmt = count_stmt.where(Conversation.name.ilike(f"%{search}%"))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Get paginated results
    stmt = stmt.order_by(Conversation.last_message_at.desc().nullslast())
    stmt = stmt.offset(offset).limit(per_page)

    result = await db.execute(stmt)
    conversations = result.scalars().all()

    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in conversations],
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page if total > 0 else 0,
    )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a single conversation by ID."""
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.participants))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return ConversationResponse.model_validate(conversation)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update: ConversationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if update.name is not None:
        conversation.name = update.name

    await db.commit()

    # Reload with participants
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.participants))
        .where(Conversation.id == conversation_id)
    )
    result = await db.execute(stmt)
    conversation = result.scalar_one()

    return ConversationResponse.model_validate(conversation)


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conversation)
    await db.commit()

    return {"status": "deleted"}


@router.post("/{conversation_id}/share")
async def generate_share_link(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Generate a share token for a conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    token = conversation.generate_share_token()
    await db.commit()

    return {"share_token": token, "share_url": f"/shared/{token}"}


@router.delete("/{conversation_id}/share")
async def revoke_share_link(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Revoke the share token for a conversation."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.revoke_share_token()
    await db.commit()

    return {"status": "revoked"}
