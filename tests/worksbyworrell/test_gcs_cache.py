from unittest.mock import MagicMock

from src.worksbyworrell.storage.gcs_cache import GCSCacheManager


def test_local_fallback_when_no_bucket(tmp_path):
    local_file = str(tmp_path / "processed_links.txt")
    with open(local_file, "w") as f:
        f.write("https://example.com/1\nhttps://example.com/2\n")

    manager = GCSCacheManager(
        bucket_name=None, local_processed_file=local_file, use_env_default=False
    )
    links = manager.download_processed_links()

    assert links == {"https://example.com/1", "https://example.com/2"}


def test_upload_local_fallback(tmp_path):
    local_file = str(tmp_path / "processed_links.txt")
    manager = GCSCacheManager(
        bucket_name=None, local_processed_file=local_file, use_env_default=False
    )

    test_links = {"https://example.com/a", "https://example.com/b"}
    result = manager.upload_processed_links(test_links)

    assert result is True
    with open(local_file, "r") as f:
        content = f.read().splitlines()
    assert set(content) == test_links


def test_gcs_merge_and_upload(tmp_path):
    local_file = str(tmp_path / "processed_links.txt")
    with open(local_file, "w") as f:
        f.write("https://example.com/local1\n")

    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    mock_blob.exists.return_value = True
    mock_blob.download_as_text.return_value = "https://example.com/remote1\n"

    manager = GCSCacheManager(bucket_name="test-bucket", local_processed_file=local_file)
    manager._client = mock_client

    links = manager.download_processed_links()
    assert links == {"https://example.com/local1", "https://example.com/remote1"}

    upload_result = manager.upload_processed_links(links)
    assert upload_result is True
    mock_blob.upload_from_string.assert_called_once()
