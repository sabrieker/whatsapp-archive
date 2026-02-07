from fastapi import APIRouter
from .conversations import router as conversations_router
from .messages import router as messages_router
from .import_ import router as import_router
from .search import router as search_router
from .media import router as media_router
from .shared import router as shared_router
from .analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(conversations_router, prefix="/conversations", tags=["conversations"])
api_router.include_router(messages_router, prefix="/messages", tags=["messages"])
api_router.include_router(import_router, prefix="/import", tags=["import"])
api_router.include_router(search_router, prefix="/search", tags=["search"])
api_router.include_router(media_router, prefix="/media", tags=["media"])
api_router.include_router(shared_router, prefix="/shared", tags=["shared"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["analytics"])
