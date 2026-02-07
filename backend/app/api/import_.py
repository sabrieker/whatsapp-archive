from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas import (
    ImportJobCreate,
    ImportJobResponse,
    ChunkUploadResponse,
    ImportStartRequest,
    ImportProgressResponse,
)
from ..services.importer import ImporterService

router = APIRouter()


@router.post("/init", response_model=ImportJobResponse)
async def init_import(
    job_data: ImportJobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Initialize a new import job for chunked upload."""
    importer = ImporterService(db)
    job = await importer.create_import_job(
        filename=job_data.filename,
        file_size=job_data.file_size,
        total_chunks=job_data.total_chunks,
    )
    return ImportJobResponse.model_validate(job)


@router.post("/upload/chunk", response_model=ChunkUploadResponse)
async def upload_chunk(
    job_id: int = Form(...),
    chunk_number: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a chunk of the import file."""
    chunk_data = await file.read()

    importer = ImporterService(db)
    job = await importer.upload_chunk(job_id, chunk_number, chunk_data)

    return ChunkUploadResponse(
        job_id=job.id,
        chunk_number=chunk_number,
        uploaded_chunks=job.uploaded_chunks,
        total_chunks=job.total_chunks,
        complete=job.uploaded_chunks >= job.total_chunks,
    )


@router.post("/upload/simple", response_model=ImportJobResponse)
async def upload_simple(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Simple single-file upload for smaller files (< 100MB recommended)."""
    content = await file.read()

    importer = ImporterService(db)

    # Create job
    job = await importer.create_import_job(
        filename=file.filename or "upload.txt",
        file_size=len(content),
        total_chunks=1,
    )

    # Upload as single chunk
    job = await importer.upload_chunk(job.id, 0, content)

    return ImportJobResponse.model_validate(job)


@router.post("/start", response_model=ImportJobResponse)
async def start_import(
    request: ImportStartRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start processing an uploaded import file."""
    importer = ImporterService(db)
    job = await importer.start_import(request.job_id)
    return ImportJobResponse.model_validate(job)


@router.get("/progress/{job_id}", response_model=ImportProgressResponse)
async def get_import_progress(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the progress of an import job."""
    importer = ImporterService(db)
    job = await importer.get_import_progress(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")

    # Calculate progress percentage
    progress = 0.0
    if job.status == "uploading":
        if job.total_chunks > 0:
            progress = (job.uploaded_chunks / job.total_chunks) * 50  # Upload is 50%
    elif job.status == "processing":
        if job.total_messages > 0:
            msg_progress = (job.processed_messages / job.total_messages) * 40
            media_progress = 0
            if job.total_media > 0:
                media_progress = (job.processed_media / job.total_media) * 10
            progress = 50 + msg_progress + media_progress  # Processing is other 50%
    elif job.status == "completed":
        progress = 100.0

    return ImportProgressResponse(
        job_id=job.id,
        status=job.status,
        progress_percent=progress,
        total_messages=job.total_messages,
        processed_messages=job.processed_messages,
        total_media=job.total_media,
        processed_media=job.processed_media,
        error_message=job.error_message,
    )


@router.get("/jobs", response_model=list[ImportJobResponse])
async def list_import_jobs(
    db: AsyncSession = Depends(get_db),
):
    """List all import jobs."""
    from sqlalchemy import select
    from ..models import ImportJob

    stmt = select(ImportJob).order_by(ImportJob.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    jobs = result.scalars().all()

    return [ImportJobResponse.model_validate(j) for j in jobs]
