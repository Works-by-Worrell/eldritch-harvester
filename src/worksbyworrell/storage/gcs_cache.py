import logging
import os
from typing import Optional, Set

logger = logging.getLogger(__name__)


class GCSCacheManager:
    """Manages cache synchronization with GCP Cloud Storage."""

    def __init__(
        self,
        bucket_name: Optional[str] = None,
        local_processed_file: str = "processed_links.txt",
        use_env_default: bool = True,
    ):
        if bucket_name is not None:
            self.bucket_name = bucket_name
        elif use_env_default:
            self.bucket_name = os.environ.get("GCS_BUCKET_NAME")
        else:
            self.bucket_name = None
        self.local_processed_file = local_processed_file
        self._client = None

    @property
    def client(self):
        if self._client is None and self.bucket_name:
            try:
                from google.cloud import storage

                self._client = storage.Client()
            except Exception as e:
                logger.warning(
                    f"GCS Client initialization failed: {e}. Falling back to local state."
                )
                self._client = None
        return self._client

    def download_processed_links(self) -> Set[str]:
        """Load processed links from local file system and merge with GCS cache if configured."""
        links: Set[str] = set()

        if os.path.exists(self.local_processed_file):
            try:
                with open(self.local_processed_file, "r", encoding="utf-8") as f:
                    links.update(line.strip() for line in f if line.strip())
            except Exception as e:
                logger.error(f"Error reading local {self.local_processed_file}: {e}")

        if self.bucket_name and self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob("cache/processed_links.txt")
                if blob.exists():
                    remote_content = blob.download_as_text()
                    remote_links = set(
                        line.strip() for line in remote_content.splitlines() if line.strip()
                    )
                    links.update(remote_links)
                    logger.info(
                        f"Merged {len(remote_links)} links from GCS bucket {self.bucket_name}."
                    )
            except Exception as e:
                logger.warning(f"Failed to fetch processed_links from GCS: {e}")

        return links

    def upload_processed_links(self, links: Set[str]) -> bool:
        """Persist processed links set to local disk and upload to GCS."""
        try:
            sorted_links = sorted(list(links))
            with open(self.local_processed_file, "w", encoding="utf-8") as f:
                for link in sorted_links:
                    f.write(f"{link}\n")
        except Exception as e:
            logger.error(f"Failed to write local processed links: {e}")
            return False

        if self.bucket_name and self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob = bucket.blob("cache/processed_links.txt")
                content = "\n".join(sorted(list(links))) + "\n"
                blob.upload_from_string(content, content_type="text/plain")
                logger.info(f"Uploaded {len(links)} links to GCS bucket {self.bucket_name}.")
                return True
            except Exception as e:
                logger.warning(f"Failed to upload processed_links to GCS: {e}")
                return False

        return True

    def sync_rejection_log(self, local_log_file: str, date_str: str) -> bool:
        """Upload rejection log file to GCS logs/ folder."""
        if not os.path.exists(local_log_file):
            return False

        if self.bucket_name and self.client:
            try:
                bucket = self.client.bucket(self.bucket_name)
                blob_name = f"logs/clutch_rejects_{date_str}.log"
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(local_log_file)
                logger.info(f"Synced rejection log to GCS gs://{self.bucket_name}/{blob_name}")
                return True
            except Exception as e:
                logger.warning(f"Failed to sync rejection log to GCS: {e}")
                return False

        return True
