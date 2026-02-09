"""Tests for app.services.translator_service — Azure Translator EN to HI/TE."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# Fixtures: configured / unconfigured TranslatorService
# ---------------------------------------------------------------------------


@pytest.fixture
def unconfigured_translator():
    """TranslatorService with empty key => not configured."""
    with patch("app.services.translator_service.settings") as mock_settings:
        mock_settings.azure_translator_key = ""
        mock_settings.azure_translator_region = "centralindia"
        from app.services.translator_service import TranslatorService

        svc = TranslatorService()
        assert not svc.configured
        return svc


@pytest.fixture
def configured_translator():
    """TranslatorService with a fake key => configured."""
    with patch("app.services.translator_service.settings") as mock_settings:
        mock_settings.azure_translator_key = "fake-key"
        mock_settings.azure_translator_region = "centralindia"
        from app.services.translator_service import TranslatorService

        svc = TranslatorService()
        assert svc.configured
        return svc


# ---------------------------------------------------------------------------
# Helper: build a mock httpx.AsyncClient context manager
# ---------------------------------------------------------------------------


def _make_httpx_mock(json_response):
    """Return a patched httpx.AsyncClient that yields a mock with .post()."""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = json_response
    mock_response.raise_for_status = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


# ---------------------------------------------------------------------------
# Tests: __init__
# ---------------------------------------------------------------------------


class TestInit:
    """TranslatorService.__init__ sets .configured based on the key."""

    def test_configured_when_key_present(self, configured_translator):
        assert configured_translator.configured is True

    def test_not_configured_when_key_empty(self, unconfigured_translator):
        assert unconfigured_translator.configured is False


# ---------------------------------------------------------------------------
# Tests: translate()
# ---------------------------------------------------------------------------


class TestTranslate:
    """TranslatorService.translate — six scenarios."""

    @pytest.mark.asyncio
    async def test_en_to_hi_success(self, configured_translator):
        """EN->HI: mock API returns Hindi text."""
        mock_client = _make_httpx_mock(
            [{"translations": [{"text": "\u0928\u092e\u0938\u094d\u0924\u0947"}]}]
        )
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.translate("Hello", target_language="hi")
            assert result == "\u0928\u092e\u0938\u094d\u0924\u0947"

    @pytest.mark.asyncio
    async def test_en_to_te_success(self, configured_translator):
        """EN->TE: mock API returns Telugu text."""
        mock_client = _make_httpx_mock(
            [{"translations": [{"text": "\u0c38\u0c4d\u0c35\u0c3e\u0c17\u0c24\u0c02"}]}]
        )
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.translate(
                "Welcome", target_language="te"
            )
            assert result == "\u0c38\u0c4d\u0c35\u0c3e\u0c17\u0c24\u0c02"

    @pytest.mark.asyncio
    async def test_same_language_returns_original(self, configured_translator):
        """When target == source, return text immediately (no API call)."""
        with patch(
            "app.services.translator_service.httpx.AsyncClient"
        ) as MockHttpx:
            result = await configured_translator.translate(
                "Hello", target_language="en", source_language="en"
            )
            assert result == "Hello"
            MockHttpx.assert_not_called()

    @pytest.mark.asyncio
    async def test_not_configured_returns_original(self, unconfigured_translator):
        """When azure_translator_key is empty, returns original text."""
        result = await unconfigured_translator.translate("Hello", target_language="hi")
        assert result == "Hello"

    @pytest.mark.asyncio
    async def test_unsupported_language_returns_original(self, configured_translator):
        """'fr' is not in SUPPORTED_LANGUAGES, so returns original text."""
        with patch(
            "app.services.translator_service.httpx.AsyncClient"
        ) as MockHttpx:
            result = await configured_translator.translate(
                "Hello", target_language="fr"
            )
            assert result == "Hello"
            MockHttpx.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_error_returns_original(self, configured_translator):
        """When httpx raises an exception, returns original text."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Connection timeout"))
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.translate(
                "Hello", target_language="hi"
            )
            assert result == "Hello"


# ---------------------------------------------------------------------------
# Tests: detect_language()
# ---------------------------------------------------------------------------


class TestDetectLanguage:
    """TranslatorService.detect_language — four scenarios."""

    @pytest.mark.asyncio
    async def test_detect_hindi(self, configured_translator):
        """Detect Hindi text."""
        mock_client = _make_httpx_mock([{"language": "hi"}])
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.detect_language(
                "\u0928\u092e\u0938\u094d\u0924\u0947"
            )
            assert result == "hi"

    @pytest.mark.asyncio
    async def test_detect_english(self, configured_translator):
        """Detect English text."""
        mock_client = _make_httpx_mock([{"language": "en"}])
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.detect_language("Hello world")
            assert result == "en"

    @pytest.mark.asyncio
    async def test_not_configured_returns_en(self, unconfigured_translator):
        """When not configured, defaults to 'en'."""
        result = await unconfigured_translator.detect_language(
            "\u0928\u092e\u0938\u094d\u0924\u0947"
        )
        assert result == "en"

    @pytest.mark.asyncio
    async def test_api_error_returns_en(self, configured_translator):
        """When httpx raises, defaults to 'en'."""
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=Exception("Service unavailable"))
        with patch(
            "app.services.translator_service.httpx.AsyncClient",
            return_value=mock_client,
        ):
            result = await configured_translator.detect_language("some text")
            assert result == "en"
