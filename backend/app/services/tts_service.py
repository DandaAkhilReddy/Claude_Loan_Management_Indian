"""Azure Neural TTS service — minimal "Listen" button on AI explanations.

Free tier: 500K characters/month.
Voices: en-IN-NeerjaNeural, hi-IN-SwaraNeural, te-IN-ShrutiNeural
"""

import logging
import base64
from xml.sax.saxutils import escape as xml_escape
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

VOICE_MAP = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "te": "te-IN-ShrutiNeural",
}

TTS_ENDPOINT = "https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"


class TTSService:
    """Azure Neural TTS for generating audio from AI explanations."""

    def __init__(self):
        self.key = settings.azure_tts_key
        self.region = settings.azure_tts_region
        self.configured = bool(self.key)
        if not self.configured:
            logger.warning("Azure TTS not configured")

    async def generate_audio(self, text: str, language: str = "en") -> str | None:
        """Generate speech audio from text.

        Args:
            text: Text to convert to speech
            language: Language code ('en', 'hi', 'te')

        Returns:
            Base64-encoded MP3 audio string, or None if failed
        """
        if not self.configured:
            return None

        # Validate language against allowlist to prevent XML injection in SSML
        if language not in VOICE_MAP:
            language = "en"
        voice = VOICE_MAP[language]
        endpoint = TTS_ENDPOINT.format(region=self.region)

        safe_text = xml_escape(text)
        ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{language}'>
    <voice name='{voice}'>
        <prosody rate='0.9'>{safe_text}</prosody>
    </voice>
</speak>"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Ocp-Apim-Subscription-Key": self.key,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": "audio-16khz-128kbitrate-mono-mp3",
                    },
                    content=ssml.encode("utf-8"),
                    timeout=30.0,
                )
                response.raise_for_status()
                audio_base64 = base64.b64encode(response.content).decode("utf-8")
                return audio_base64
        except Exception as e:
            logger.error(f"TTS generation error: {e}")
            return None
