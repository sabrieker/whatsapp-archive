from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from .config import get_settings
from .database import init_db
from .api import api_router

settings = get_settings()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting up...")

    # Initialize database tables
    await init_db()
    logger.info("Database initialized")

    # Ensure MinIO bucket exists
    try:
        from .services.storage import StorageService
        StorageService()  # This will create the bucket if it doesn't exist
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Could not initialize storage: {e}")

    yield

    logger.info("Shutting down...")


app = FastAPI(
    title="WhatsApp Archive",
    description="A WhatsApp Web-like archive viewer for reading and searching exported chats",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "whatsapp-archive"}


@app.get("/health")
async def health():
    """Detailed health check."""
    from sqlalchemy import text
    from .database import engine

    health_status = {"status": "ok", "database": "unknown", "storage": "unknown"}

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "ok"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    # Check storage
    try:
        from .services.storage import StorageService
        storage = StorageService()
        storage.client.bucket_exists(settings.minio_bucket)
        health_status["storage"] = "ok"
    except Exception as e:
        health_status["storage"] = f"error: {str(e)}"
        health_status["status"] = "degraded"

    return health_status
