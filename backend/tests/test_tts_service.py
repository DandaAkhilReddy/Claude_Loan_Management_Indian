"""Tests for app.services.tts_service — Azure Neural TTS."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from xml.sax.saxutils import escape as xml_escape

from app.services.tts_service import VOICE_MAP


# ---------------------------------------------------------------------------
# Fixture: unconfigured TTSService (key="")
# ---------------------------------------------------------------------------


@pytest.fixture
def unconfigured_tts():
    """TTSService with empty key => not configured."""
    with patch("app.services.tts_service.settings") as mock_settings:
        mock_settings.azure_tts_key = ""
        mock_settings.azure_tts_region = "centralindia"
        from app.services.tts_service import TTSService

        svc = TTSService()
        assert not svc.configured
        return svc


@pytest.fixture
def configured_tts():
    """TTSService with a fake key => configured."""
    with patch("app.services.tts_service.settings") as mock_settings:
        mock_settings.azure_tts_key = "fake-tts-key"
        mock_settings.azure_tts_region = "centralindia"
        from app.services.tts_service import TTSService

        svc = TTSService()
        assert svc.configured
        return svc


# ---------------------------------------------------------------------------
# Tests: not configured
# ---------------------------------------------------------------------------


class TestTTSNotConfigured:

    @pytest.mark.asyncio
    async def test_not_configured_returns_none(self, unconfigured_tts):
        """When azure_tts_key is empty, generate_audio returns None."""
        result = await unconfigured_tts.generate_audio("Hello world", language="en")
        assert result is None

    @pytest.mark.asyncio
    async def test_not_configured_any_language(self, unconfigured_tts):
        """Even with a valid language code, returns None if not configured."""
        result = await unconfigured_tts.generate_audio("Namaste", language="hi")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: language fallback
# ---------------------------------------------------------------------------


class TestLanguageFallback:

    @pytest.mark.asyncio
    async def test_invalid_language_defaults_to_en(self, configured_tts):
        """An invalid language code should fall back to 'en' voice."""
        with patch("app.services.tts_service.httpx.AsyncClient") as MockHttpx:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.content = b"fake-audio-bytes"
            mock_response.raise_for_status = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=mock_response)
            MockHttpx.return_value = mock_client

            result = await configured_tts.generate_audio("Hello", language="xyz")

            assert result is not None
            # Verify the SSML contains the English voice (fallback)
            call_args = mock_client.post.call_args
            ssml_bytes = call_args.kwargs.get("content") or call_args[1].get("content")
            ssml_str = ssml_bytes.decode("utf-8")
            assert "en-IN-NeerjaNeural" in ssml_str


# ---------------------------------------------------------------------------
# Tests: xml_escape for SSML safety
# ---------------------------------------------------------------------------


class TestXmlEscape:

    def test_escapes_ampersand(self):
        assert xml_escape("A & B") == "A &amp; B"

    def test_escapes_less_than(self):
        assert xml_escape("a < b") == "a &lt; b"

    def test_escapes_greater_than(self):
        assert xml_escape("a > b") == "a &gt; b"

    def test_escapes_single_quote(self):
        result = xml_escape("it's", entities={"'": "&apos;"})
        assert result == "it&apos;s"

    def test_escapes_double_quote(self):
        result = xml_escape('say "hello"', entities={'"': "&quot;"})
        assert result == "say &quot;hello&quot;"

    def test_combined_special_chars(self):
        text = '<script>alert("xss")</script> & more'
        escaped = xml_escape(text)
        assert "&lt;" in escaped
        assert "&gt;" in escaped
        assert "&amp;" in escaped

    def test_plain_text_unchanged(self):
        text = "Your loan is approved"
        assert xml_escape(text) == text


# ---------------------------------------------------------------------------
# Tests: VOICE_MAP keys
# ---------------------------------------------------------------------------


class TestVoiceMap:

    def test_voice_map_has_en(self):
        assert "en" in VOICE_MAP

    def test_voice_map_has_hi(self):
        assert "hi" in VOICE_MAP

    def test_voice_map_has_te(self):
        assert "te" in VOICE_MAP

    def test_voice_map_en_value(self):
        assert VOICE_MAP["en"] == "en-IN-NeerjaNeural"

    def test_voice_map_hi_value(self):
        assert VOICE_MAP["hi"] == "hi-IN-SwaraNeural"

    def test_voice_map_te_value(self):
        assert VOICE_MAP["te"] == "te-IN-ShrutiNeural"

    def test_voice_map_exactly_three_keys(self):
        assert len(VOICE_MAP) == 3
