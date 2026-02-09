"""Tests for Azure Blob Storage service (blob_service.py).

All Azure SDK classes are pre-mocked via conftest.py sys.modules patches.
We patch `app.config.settings` to control BlobService.__init__ behavior.
"""

from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# Helper: build a BlobService with controlled settings
# ---------------------------------------------------------------------------

def _make_service(connection_string="DefaultEndpointsProtocol=https;AccountName=test;AccountKey=abc123;EndpointSuffix=core.windows.net",
                  container="loan-documents"):
    """Create a BlobService instance with patched settings."""
    mock_settings = MagicMock()
    mock_settings.azure_storage_connection_string = connection_string
    mock_settings.azure_storage_container = container

    with patch("app.services.blob_service.settings", mock_settings):
        from app.services.blob_service import BlobService
        svc = BlobService()
    return svc


def _make_unconfigured_service():
    """Create a BlobService with no connection string (disabled)."""
    return _make_service(connection_string="")


# ===========================================================================
# TestInit
# ===========================================================================

class TestInit:
    """BlobService.__init__ behaviour."""

    def test_configured_client_is_not_none(self):
        """When a connection string is provided, client should be set."""
        svc = _make_service()
        assert svc.client is not None

    def test_unconfigured_client_is_none(self):
        """When the connection string is empty, client should be None."""
        svc = _make_unconfigured_service()
        assert svc.client is None


# ===========================================================================
# TestUploadFile
# ===========================================================================

class TestUploadFile:
    """BlobService.upload_file tests."""

    async def test_upload_success_returns_url(self):
        svc = _make_service()

        # Wire up the mock chain: client -> container_client -> blob_client
        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://test.blob.core.windows.net/loan-documents/user1/somefile.pdf"
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        svc.client.get_container_client.return_value = mock_container_client

        result = await svc.upload_file(
            content=b"PDF_CONTENT",
            filename="statement.pdf",
            content_type="application/pdf",
            user_id="user1",
        )

        assert isinstance(result, str)
        assert result == mock_blob_client.url

    async def test_blob_name_contains_user_id(self):
        svc = _make_service()

        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://test.blob.core.windows.net/loan-documents/user42/abc.pdf"
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        svc.client.get_container_client.return_value = mock_container_client

        await svc.upload_file(b"data", "file.pdf", "application/pdf", "user42")

        # get_blob_client is called with a blob_name that starts with "user42/"
        blob_name_arg = mock_container_client.get_blob_client.call_args[0][0]
        assert blob_name_arg.startswith("user42/")

    async def test_create_container_is_called(self):
        svc = _make_service()

        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/loan-documents/u/f.pdf"
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        svc.client.get_container_client.return_value = mock_container_client

        await svc.upload_file(b"data", "f.pdf", "application/pdf", "u")

        mock_container_client.create_container.assert_called_once()

    async def test_not_configured_raises_runtime_error(self):
        svc = _make_unconfigured_service()

        with pytest.raises(RuntimeError, match="not configured"):
            await svc.upload_file(b"data", "f.pdf", "application/pdf", "u")

    async def test_content_type_is_forwarded(self):
        svc = _make_service()

        mock_blob_client = MagicMock()
        mock_blob_client.url = "https://example.com/loan-documents/u/f.png"
        mock_container_client = MagicMock()
        mock_container_client.get_blob_client.return_value = mock_blob_client
        svc.client.get_container_client.return_value = mock_container_client

        await svc.upload_file(b"img", "photo.png", "image/png", "u")

        # upload_blob should have been called with content_type="image/png"
        mock_blob_client.upload_blob.assert_called_once()
        _, kwargs = mock_blob_client.upload_blob.call_args
        assert kwargs["content_type"] == "image/png"


# ===========================================================================
# TestGenerateSasUrl
# ===========================================================================

class TestGenerateSasUrl:
    """BlobService.generate_sas_url tests."""

    async def test_success_returns_url_with_token(self):
        svc = _make_service(container="loan-documents")

        # Provide account_name and credential on the mock client
        svc.client.account_name = "teststorage"
        svc.client.credential = MagicMock()
        svc.client.credential.account_key = "fakekey123"

        blob_url = "https://teststorage.blob.core.windows.net/loan-documents/user1/file.pdf"

        with patch("app.services.blob_service.generate_blob_sas", return_value="sv=2023&sig=abc") as mock_sas:
            result = await svc.generate_sas_url(blob_url, expiry_hours=2)

        assert "?" in result
        assert result.startswith(blob_url)
        assert "sv=2023&sig=abc" in result

    async def test_not_configured_returns_original_url(self):
        svc = _make_unconfigured_service()
        original = "https://example.com/loan-documents/user1/file.pdf"
        result = await svc.generate_sas_url(original)
        assert result == original

    async def test_invalid_url_format_returns_original(self):
        svc = _make_service(container="loan-documents")
        # URL that does not contain the container name at all
        bad_url = "https://example.com/other-container/file.pdf"
        result = await svc.generate_sas_url(bad_url)
        assert result == bad_url

    async def test_generate_blob_sas_called_with_correct_args(self):
        svc = _make_service(container="loan-documents")
        svc.client.account_name = "myaccount"
        svc.client.credential = MagicMock()
        svc.client.credential.account_key = "mykey"

        blob_url = "https://myaccount.blob.core.windows.net/loan-documents/uid/doc.pdf"

        with patch("app.services.blob_service.generate_blob_sas", return_value="tok") as mock_sas:
            await svc.generate_sas_url(blob_url, expiry_hours=3)

        mock_sas.assert_called_once()
        kwargs = mock_sas.call_args[1]
        assert kwargs["account_name"] == "myaccount"
        assert kwargs["container_name"] == "loan-documents"
        assert kwargs["blob_name"] == "uid/doc.pdf"
        assert kwargs["account_key"] == "mykey"


# ===========================================================================
# TestDeleteBlob
# ===========================================================================

class TestDeleteBlob:
    """BlobService.delete_blob tests."""

    async def test_success_returns_true(self):
        svc = _make_service(container="loan-documents")

        mock_container_client = MagicMock()
        svc.client.get_container_client.return_value = mock_container_client

        blob_url = "https://test.blob.core.windows.net/loan-documents/user1/file.pdf"
        result = await svc.delete_blob(blob_url)

        assert result is True
        mock_container_client.delete_blob.assert_called_once_with("user1/file.pdf")

    async def test_exception_returns_false(self):
        svc = _make_service(container="loan-documents")

        mock_container_client = MagicMock()
        mock_container_client.delete_blob.side_effect = Exception("Boom")
        svc.client.get_container_client.return_value = mock_container_client

        blob_url = "https://test.blob.core.windows.net/loan-documents/user1/file.pdf"
        result = await svc.delete_blob(blob_url)

        assert result is False

    async def test_not_configured_returns_false(self):
        svc = _make_unconfigured_service()
        result = await svc.delete_blob("https://example.com/loan-documents/user1/file.pdf")
        assert result is False

    async def test_invalid_url_returns_false(self):
        svc = _make_service(container="loan-documents")
        # URL without the container name, so split produces < 2 parts
        result = await svc.delete_blob("https://example.com/no-match/file.pdf")
        assert result is False
