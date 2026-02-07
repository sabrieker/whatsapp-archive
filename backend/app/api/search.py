from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..database import get_db
from ..schemas import MessageResponse, MessageListResponse
from ..services.search import SearchService
from ..services.storage import StorageService

router = APIRouter()


@router.get("", response_model=MessageListResponse)
async def search_messages(
    q: str = Query(..., min_length=1, description="Search query"),
    conversation_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Search messages using full-text search."""
    search_service = SearchService(db)
    results = await search_service.search_messages(
        query=q,
        conversation_id=conversation_id,
        page=page,
        per_page=per_page,
    )

    # Enrich with participant colors
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
