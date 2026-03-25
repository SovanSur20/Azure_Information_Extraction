from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient
from azure.core.exceptions import ResourceNotFoundError
from typing import Optional, List, BinaryIO
import logging
from io import BytesIO

from src.config.settings import settings
from src.auth.azure_auth import auth_manager
from src.logging.logger import centralized_logger


class StorageService:
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._initialize_client()

    def _initialize_client(self) -> None:
        try:
            credential = auth_manager.get_credential()
            self.blob_service_client = BlobServiceClient(
                account_url=settings.storage_account_url,
                credential=credential
            )
            self.logger.info("Storage service initialized with managed identity")
        except Exception as e:
            self.logger.error(f"Failed to initialize storage service: {str(e)}")
            raise

    def get_container_client(self, container_name: str) -> ContainerClient:
        return self.blob_service_client.get_container_client(container_name)

    def get_blob_client(self, container_name: str, blob_name: str) -> BlobClient:
        return self.blob_service_client.get_blob_client(
            container=container_name,
            blob=blob_name
        )

    def download_blob(self, container_name: str, blob_name: str) -> bytes:
        try:
            blob_client = self.get_blob_client(container_name, blob_name)
            
            start_time = self._get_current_time_ms()
            blob_data = blob_client.download_blob().readall()
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.track_dependency(
                name="Azure Blob Storage",
                data=f"Download {blob_name}",
                duration=duration,
                success=True
            )
            
            self.logger.info(f"Downloaded blob: {blob_name} ({len(blob_data)} bytes)")
            return blob_data
            
        except ResourceNotFoundError:
            self.logger.error(f"Blob not found: {blob_name}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to download blob {blob_name}: {str(e)}")
            raise

    def upload_blob(
        self,
        container_name: str,
        blob_name: str,
        data: bytes,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None,
        overwrite: bool = True
    ) -> str:
        try:
            blob_client = self.get_blob_client(container_name, blob_name)
            
            start_time = self._get_current_time_ms()
            blob_client.upload_blob(
                data,
                overwrite=overwrite,
                content_settings={'content_type': content_type} if content_type else None,
                metadata=metadata
            )
            duration = self._get_current_time_ms() - start_time
            
            centralized_logger.track_dependency(
                name="Azure Blob Storage",
                data=f"Upload {blob_name}",
                duration=duration,
                success=True
            )
            
            blob_url = blob_client.url
            self.logger.info(f"Uploaded blob: {blob_name} ({len(data)} bytes)")
            return blob_url
            
        except Exception as e:
            self.logger.error(f"Failed to upload blob {blob_name}: {str(e)}")
            raise

    def list_blobs(self, container_name: str, prefix: Optional[str] = None) -> List[str]:
        try:
            container_client = self.get_container_client(container_name)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            blob_names = [blob.name for blob in blobs]
            self.logger.info(f"Listed {len(blob_names)} blobs in container {container_name}")
            return blob_names
        except Exception as e:
            self.logger.error(f"Failed to list blobs: {str(e)}")
            raise

    def delete_blob(self, container_name: str, blob_name: str) -> None:
        try:
            blob_client = self.get_blob_client(container_name, blob_name)
            blob_client.delete_blob()
            self.logger.info(f"Deleted blob: {blob_name}")
        except ResourceNotFoundError:
            self.logger.warning(f"Blob not found for deletion: {blob_name}")
        except Exception as e:
            self.logger.error(f"Failed to delete blob {blob_name}: {str(e)}")
            raise

    def blob_exists(self, container_name: str, blob_name: str) -> bool:
        try:
            blob_client = self.get_blob_client(container_name, blob_name)
            return blob_client.exists()
        except Exception as e:
            self.logger.error(f"Failed to check blob existence: {str(e)}")
            return False

    def get_blob_url(self, container_name: str, blob_name: str) -> str:
        blob_client = self.get_blob_client(container_name, blob_name)
        return blob_client.url

    @staticmethod
    def _get_current_time_ms() -> int:
        from datetime import datetime
        return int(datetime.utcnow().timestamp() * 1000)


storage_service = StorageService()
