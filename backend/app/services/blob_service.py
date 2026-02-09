"""Azure Blob Storage service — upload, SAS URL, delete."""

import uuid
import logging
from datetime import datetime, timedelta, timezone

from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions

from app.config import settings

logger = logging.getLogger(__name__)


class BlobService:
    """Azure Blob Storage for loan document uploads."""

    def __init__(self):
        if settings.azure_storage_connection_string:
            self.client = BlobServiceClient.from_connection_string(
                settings.azure_storage_connection_string
            )
            self.container_name = settings.azure_storage_container
        else:
            self.client = None
            logger.warning("Azure Blob Storage not configured")

    @property
    def is_configured(self) -> bool:
        return self.client is not None

    async def upload_file(
        self, content: bytes, filename: str, content_type: str, user_id: str
    ) -> str:
        """Upload file to Azure Blob Storage.

        Returns: Blob URL
        """
        if not self.client:
            raise RuntimeError("Azure Blob Storage not configured")

        # Generate unique blob name
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        blob_name = f"{user_id}/{uuid.uuid4()}.{ext}"

        container_client = self.client.get_container_client(self.container_name)

        # Ensure container exists
        try:
            await container_client.create_container()
        except Exception:
            pass  # Already exists

        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(content, content_type=content_type, overwrite=True)

        return blob_client.url

    async def generate_sas_url(self, blob_url: str, expiry_hours: int = 1) -> str:
        """Generate time-limited SAS URL for reading a blob."""
        if not self.client:
            return blob_url

        # Extract blob name from URL
        parts = blob_url.split(f"{self.container_name}/")
        if len(parts) < 2:
            return blob_url

        blob_name = parts[1]
        account_name = self.client.account_name

        sas_token = generate_blob_sas(
            account_name=account_name,
            container_name=self.container_name,
            blob_name=blob_name,
            account_key=self.client.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )

        return f"{blob_url}?{sas_token}"

    async def delete_blob(self, blob_url: str) -> bool:
        """Delete a blob by URL."""
        if not self.client:
            return False

        try:
            parts = blob_url.split(f"{self.container_name}/")
            if len(parts) < 2:
                return False
            blob_name = parts[1]
            container_client = self.client.get_container_client(self.container_name)
            container_client.delete_blob(blob_name)
            return True
        except Exception as e:
            logger.error(f"Blob deletion error: {e}")
            return False
