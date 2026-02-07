from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..models import Conversation
from ..services.analytics import AnalyticsService

router = APIRouter()


@router.get("/{conversation_id}")
async def get_cached_analytics(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get cached analytics if available."""
    # Verify conversation exists
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    analytics_service = AnalyticsService(db)
    result = analytics_service.get_cached_analytics(conversation_id)

    if result:
        return result

    # Return 404 if no cached analytics
    raise HTTPException(status_code=404, detail="No cached analytics found")


@router.post("/{conversation_id}")
async def generate_analytics(
    conversation_id: int,
    person1: Optional[str] = Query(None, description="First person to compare"),
    person2: Optional[str] = Query(None, description="Second person to compare"),
    db: AsyncSession = Depends(get_db),
):
    """Generate analytics charts for a conversation."""
    # Verify conversation exists
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        analytics_service = AnalyticsService(db)
        result = await analytics_service.generate_analytics(
            conversation_id,
            person1=person1,
            person2=person2,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate analytics: {str(e)}")


@router.get("/{conversation_id}/participants")
async def get_analytics_participants(
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get participants for analytics selection."""
    conversation = await db.get(Conversation, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    analytics_service = AnalyticsService(db)
    participants = await analytics_service.get_participants(conversation_id)

    return {"participants": participants}
