from minio import Minio
from minio.error import S3Error
from io import BytesIO
from typing import Optional, BinaryIO
import logging
from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class StorageService:
    """MinIO storage service for media files."""

    def __init__(self):
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        """Ensure the bucket exists."""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"Error ensuring bucket: {e}")
            raise

    def upload_file(
        self,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a file to MinIO."""
        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data,
                length,
                content_type=content_type,
            )
            logger.info(f"Uploaded: {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading {object_name}: {e}")
            raise

    def upload_bytes(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload bytes to MinIO."""
        return self.upload_file(
            object_name,
            BytesIO(data),
            len(data),
            content_type,
        )

    def download_file(self, object_name: str) -> bytes:
        """Download a file from MinIO."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error as e:
            logger.error(f"Error downloading {object_name}: {e}")
            raise

    def download_bytes(self, object_name: str) -> Optional[bytes]:
        """Download a file from MinIO, returns None if not found."""
        try:
            response = self.client.get_object(self.bucket, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error:
            return None

    def get_presigned_url(
        self,
        object_name: str,
        expires_hours: int = 1,
    ) -> str:
        """Generate a presigned URL for temporary access."""
        from datetime import timedelta

        try:
            url = self.client.presigned_get_object(
                self.bucket,
                object_name,
                expires=timedelta(hours=expires_hours),
            )
            return url
        except S3Error as e:
            logger.error(f"Error generating presigned URL for {object_name}: {e}")
            raise

    def delete_file(self, object_name: str):
        """Delete a file from MinIO."""
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Deleted: {object_name}")
        except S3Error as e:
            logger.error(f"Error deleting {object_name}: {e}")
            raise

    def list_objects(self, prefix: str = "") -> list[str]:
        """List objects with a given prefix."""
        try:
            objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing objects: {e}")
            raise

    def object_exists(self, object_name: str) -> bool:
        """Check if an object exists."""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def get_object_info(self, object_name: str) -> Optional[dict]:
        """Get object metadata."""
        try:
            stat = self.client.stat_object(self.bucket, object_name)
            return {
                "size": stat.size,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
                "etag": stat.etag,
            }
        except S3Error:
            return None

    def append_chunk(
        self,
        object_name: str,
        chunk_data: bytes,
        chunk_number: int,
    ) -> str:
        """Store a chunk for later assembly."""
        chunk_key = f"{object_name}.chunk.{chunk_number:06d}"
        self.upload_bytes(chunk_key, chunk_data)
        return chunk_key

    def assemble_chunks(
        self,
        object_name: str,
        total_chunks: int,
    ) -> str:
        """Assemble chunks into a single file."""
        # Collect all chunk data
        all_data = BytesIO()

        for i in range(total_chunks):
            chunk_key = f"{object_name}.chunk.{i:06d}"
            chunk_data = self.download_file(chunk_key)
            all_data.write(chunk_data)
            # Delete chunk after reading
            self.delete_file(chunk_key)

        # Upload assembled file
        all_data.seek(0)
        self.upload_file(
            object_name,
            all_data,
            all_data.getbuffer().nbytes,
        )

        return object_name
