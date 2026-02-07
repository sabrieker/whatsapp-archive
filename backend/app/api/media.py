from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import MediaFile
from ..services.storage import StorageService

router = APIRouter()


@router.get("/{media_id}")
async def get_media(
    media_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a media file by redirecting to a presigned URL."""
    media = await db.get(MediaFile, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    storage = StorageService()
    url = storage.get_presigned_url(media.storage_key, expires_hours=1)

    return RedirectResponse(url=url)


@router.get("/{media_id}/thumbnail")
async def get_media_thumbnail(
    media_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a media thumbnail by redirecting to a presigned URL."""
    media = await db.get(MediaFile, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    if not media.thumbnail_key:
        raise HTTPException(status_code=404, detail="Thumbnail not available")

    storage = StorageService()
    url = storage.get_presigned_url(media.thumbnail_key, expires_hours=1)

    return RedirectResponse(url=url)


@router.get("/{media_id}/info")
async def get_media_info(
    media_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get media file information."""
    media = await db.get(MediaFile, media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")

    storage = StorageService()

    return {
        "id": media.id,
        "message_id": media.message_id,
        "media_type": media.media_type,
        "mime_type": media.mime_type,
        "file_size": media.file_size,
        "original_filename": media.original_filename,
        "url": storage.get_presigned_url(media.storage_key, expires_hours=1),
        "thumbnail_url": storage.get_presigned_url(media.thumbnail_key, expires_hours=1) if media.thumbnail_key else None,
    }
