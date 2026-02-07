from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
import asyncio
import logging
import zipfile
import io
import os

from ..models import Conversation, Participant, Message, MediaFile, ImportJob
from .parser import WhatsAppParser, ParsedMessage, clean_unicode
from .storage import StorageService
from .search import SearchService

logger = logging.getLogger(__name__)


class ImporterService:
    """Service for importing WhatsApp chat exports."""

    BATCH_SIZE = 1000  # Messages per batch insert

    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = WhatsAppParser()
        self.storage = StorageService()

    async def create_import_job(
        self,
        filename: str,
        file_size: int,
        total_chunks: int,
    ) -> ImportJob:
        """Create a new import job."""
        job = ImportJob(
            filename=filename,
            file_size=file_size,
            total_chunks=total_chunks,
            status="uploading",
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def upload_chunk(
        self,
        job_id: int,
        chunk_number: int,
        chunk_data: bytes,
    ) -> ImportJob:
        """Upload a chunk of the import file."""
        job = await self.db.get(ImportJob, job_id)
        if not job:
            raise ValueError(f"Import job {job_id} not found")

        # Store chunk in MinIO
        storage_key = f"imports/{job_id}/file"
        self.storage.append_chunk(storage_key, chunk_data, chunk_number)

        # Update job progress
        job.uploaded_chunks = chunk_number + 1
        await self.db.commit()

        # Check if all chunks uploaded
        if job.uploaded_chunks >= job.total_chunks:
            # Assemble chunks
            self.storage.assemble_chunks(storage_key, job.total_chunks)
            job.temp_storage_key = storage_key
            job.status = "pending"
            await self.db.commit()

        await self.db.refresh(job)
        return job

    async def start_import(self, job_id: int) -> ImportJob:
        """Start processing an import job."""
        job = await self.db.get(ImportJob, job_id)
        if not job:
            raise ValueError(f"Import job {job_id} not found")

        if job.status != "pending":
            raise ValueError(f"Import job is not ready: {job.status}")

        job.status = "processing"
        await self.db.commit()

        # Process in background
        asyncio.create_task(self._process_import(job_id))

        await self.db.refresh(job)
        return job

    async def _process_import(self, job_id: int):
        """Process the import in the background."""
        # Create new session for background task
        from ..database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            job = await db.get(ImportJob, job_id)
            if not job:
                return

            try:
                # Download file from MinIO
                file_data = self.storage.download_file(job.temp_storage_key)

                # Check if it's a ZIP file
                if job.filename and job.filename.lower().endswith(".zip"):
                    await self._process_zip_import(db, job, file_data)
                else:
                    await self._process_text_import(db, job, file_data)

                job.status = "completed"
                job.completed_at = datetime.utcnow()

            except Exception as e:
                logger.exception(f"Import failed for job {job_id}")
                job.status = "failed"
                job.error_message = str(e)

            await db.commit()

            # Cleanup temp file
            try:
                self.storage.delete_file(job.temp_storage_key)
            except Exception:
                pass

    async def _process_text_import(
        self,
        db: AsyncSession,
        job: ImportJob,
        file_data: bytes,
    ):
        """Process a plain text chat export."""
        content = file_data.decode("utf-8", errors="replace")

        # Parse and count messages first
        messages_list = list(self.parser.parse_content(content))
        job.total_messages = len(messages_list)
        await db.commit()

        if not messages_list:
            raise ValueError("No messages found in file")

        # Create conversation
        conversation = await self._create_conversation(db, job.filename or "Imported Chat", messages_list)
        job.conversation_id = conversation.id

        # Import messages
        await self._import_messages(db, job, conversation, messages_list)

        # Update search vectors
        search_service = SearchService(db)
        await search_service.bulk_update_search_vectors(conversation.id)

    async def _process_zip_import(
        self,
        db: AsyncSession,
        job: ImportJob,
        file_data: bytes,
    ):
        """Process a ZIP file containing chat export and media."""
        with zipfile.ZipFile(io.BytesIO(file_data), "r") as zf:
            # Find the chat file
            chat_file = None
            media_files = []

            for name in zf.namelist():
                if name.endswith(".txt") and not name.startswith("__MACOSX"):
                    chat_file = name
                elif not name.endswith("/") and not name.startswith("__MACOSX"):
                    media_files.append(name)

            if not chat_file:
                raise ValueError("No chat file (.txt) found in ZIP")

            job.total_media = len(media_files)
            await db.commit()

            # Parse chat file
            chat_content = zf.read(chat_file).decode("utf-8", errors="replace")
            messages_list = list(self.parser.parse_content(chat_content))
            job.total_messages = len(messages_list)
            await db.commit()

            if not messages_list:
                raise ValueError("No messages found in chat file")

            # Extract conversation name from filename
            conv_name = os.path.splitext(os.path.basename(chat_file))[0]
            if conv_name.startswith("WhatsApp Chat with "):
                conv_name = conv_name[19:]

            # Create conversation
            conversation = await self._create_conversation(db, conv_name, messages_list)
            job.conversation_id = conversation.id

            # Import messages
            message_map = await self._import_messages(db, job, conversation, messages_list)

            # Import media files
            await self._import_media(db, job, conversation, zf, media_files, message_map)

            # Update search vectors
            search_service = SearchService(db)
            await search_service.bulk_update_search_vectors(conversation.id)

    async def _create_conversation(
        self,
        db: AsyncSession,
        name: str,
        messages: list[ParsedMessage],
    ) -> Conversation:
        """Create a conversation from parsed messages."""
        # Determine if it's a group chat
        senders = set(m.sender for m in messages if not m.is_system)
        is_group = len(senders) > 2

        # Get first and last message timestamps
        timestamps = [m.timestamp for m in messages]
        first_message = min(timestamps) if timestamps else None
        last_message = max(timestamps) if timestamps else None

        conversation = Conversation(
            name=name,
            is_group=is_group,
            message_count=len(messages),
            first_message_at=first_message,
            last_message_at=last_message,
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

        # Create participants
        for idx, sender in enumerate(sorted(senders)):
            participant = Participant(
                conversation_id=conversation.id,
                name=sender,
                color=Participant.get_color(idx),
                message_count=sum(1 for m in messages if m.sender == sender),
            )
            db.add(participant)

        await db.commit()
        return conversation

    async def _import_messages(
        self,
        db: AsyncSession,
        job: ImportJob,
        conversation: Conversation,
        messages: list[ParsedMessage],
    ) -> dict[str, int]:
        """Import messages in batches. Returns map of media filename to message ID."""
        # Get participant mapping
        stmt = select(Participant).where(Participant.conversation_id == conversation.id)
        result = await db.execute(stmt)
        participants = {p.name: p for p in result.scalars().all()}

        # Track which messages have media (by index)
        media_message_indices = {}  # index -> media_filename
        batch = []
        batch_start_idx = 0

        # Map media filename to message ID (populated after commit)
        message_map = {}

        for idx, parsed in enumerate(messages):
            participant = participants.get(parsed.sender)

            message = Message(
                conversation_id=conversation.id,
                participant_id=participant.id if participant else None,
                sender_name=parsed.sender,
                content=parsed.content,
                message_type=parsed.message_type,
                timestamp=parsed.timestamp,
                has_media=parsed.has_media,
            )
            batch.append(message)

            # Track media filename for later linking
            if parsed.media_filename:
                media_message_indices[idx] = parsed.media_filename

            # Batch insert
            if len(batch) >= self.BATCH_SIZE:
                db.add_all(batch)
                await db.flush()  # Flush to get IDs

                # Map media filenames to message IDs
                for i, msg in enumerate(batch):
                    global_idx = batch_start_idx + i
                    if global_idx in media_message_indices:
                        message_map[media_message_indices[global_idx]] = msg.id

                await db.commit()
                job.processed_messages = idx + 1
                await db.commit()
                batch_start_idx = idx + 1
                batch = []

        # Insert remaining
        if batch:
            db.add_all(batch)
            await db.flush()  # Flush to get IDs

            # Map media filenames to message IDs
            for i, msg in enumerate(batch):
                global_idx = batch_start_idx + i
                if global_idx in media_message_indices:
                    message_map[media_message_indices[global_idx]] = msg.id

            await db.commit()
            job.processed_messages = len(messages)
            await db.commit()

        return message_map

    async def _import_media(
        self,
        db: AsyncSession,
        job: ImportJob,
        conversation: Conversation,
        zf: zipfile.ZipFile,
        media_files: list[str],
        message_map: dict[str, int],
    ):
        """Import media files from ZIP. message_map is filename -> message_id."""
        for idx, media_path in enumerate(media_files):
            try:
                # Read file from ZIP
                media_data = zf.read(media_path)
                filename = os.path.basename(media_path)
                # Clean filename for matching (remove invisible unicode chars)
                clean_filename = clean_unicode(filename).strip()

                # Determine media type
                ext = os.path.splitext(filename)[1].lower()
                media_type = self._get_media_type(ext)
                mime_type = self._get_mime_type(ext)

                # Upload to MinIO
                storage_key = f"conversations/{conversation.id}/media/{clean_filename}"
                self.storage.upload_bytes(storage_key, media_data, mime_type)

                # Find associated message by ID (try both original and clean filename)
                message_id = message_map.get(clean_filename) or message_map.get(filename)
                if message_id:
                    # Create media file record
                    media_file = MediaFile(
                        message_id=message_id,
                        storage_key=storage_key,
                        original_filename=clean_filename,
                        media_type=media_type,
                        mime_type=mime_type,
                        file_size=len(media_data),
                    )
                    db.add(media_file)
                    logger.info(f"Linked media {clean_filename} to message {message_id}")
                else:
                    logger.warning(f"No message found for media: {clean_filename}")

                job.processed_media = idx + 1
                await db.commit()

            except Exception as e:
                logger.warning(f"Failed to import media {media_path}: {e}")

    def _get_media_type(self, ext: str) -> str:
        """Get media type from file extension."""
        image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        video_exts = {".mp4", ".mov", ".avi", ".webm", ".3gp"}
        audio_exts = {".mp3", ".ogg", ".opus", ".m4a", ".wav"}

        if ext in image_exts:
            return "image"
        elif ext in video_exts:
            return "video"
        elif ext in audio_exts:
            return "audio"
        else:
            return "document"

    def _get_mime_type(self, ext: str) -> str:
        """Get MIME type from file extension."""
        mime_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".mov": "video/quicktime",
            ".avi": "video/x-msvideo",
            ".webm": "video/webm",
            ".3gp": "video/3gpp",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
            ".opus": "audio/opus",
            ".m4a": "audio/mp4",
            ".wav": "audio/wav",
            ".pdf": "application/pdf",
        }
        return mime_types.get(ext, "application/octet-stream")

    async def get_import_progress(self, job_id: int) -> Optional[ImportJob]:
        """Get the current progress of an import job."""
        return await self.db.get(ImportJob, job_id)
