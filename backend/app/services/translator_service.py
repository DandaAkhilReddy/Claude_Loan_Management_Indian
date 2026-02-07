"""Azure Translator service — EN to HI/TE translation.

Free tier: 2M characters/month.
"""

import logging
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

TRANSLATOR_ENDPOINT = "https://api.cognitive.microsofttranslator.com"

SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "te": "Telugu",
}


class TranslatorService:
    """Azure Translator for multi-language AI output."""

    def __init__(self):
        self.key = settings.azure_translator_key
        self.region = settings.azure_translator_region
        self.configured = bool(self.key)
        if not self.configured:
            logger.warning("Azure Translator not configured")

    async def translate(self, text: str, target_language: str, source_language: str = "en") -> str:
        """Translate text to target language.

        Args:
            text: Source text
            target_language: Target language code ('hi', 'te', 'en')
            source_language: Source language code (default 'en')

        Returns:
            Translated text, or original text if translation fails
        """
        if not self.configured:
            return text

        if target_language == source_language:
            return text

        if target_language not in SUPPORTED_LANGUAGES:
            logger.warning(f"Unsupported language: {target_language}")
            return text

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TRANSLATOR_ENDPOINT}/translate",
                    params={
                        "api-version": "3.0",
                        "from": source_language,
                        "to": target_language,
                    },
                    headers={
                        "Ocp-Apim-Subscription-Key": self.key,
                        "Ocp-Apim-Subscription-Region": self.region,
                        "Content-Type": "application/json",
                    },
                    json=[{"text": text}],
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()
                return result[0]["translations"][0]["text"]
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text

    async def detect_language(self, text: str) -> str:
        """Detect the language of input text."""
        if not self.configured:
            return "en"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{TRANSLATOR_ENDPOINT}/detect",
                    params={"api-version": "3.0"},
                    headers={
                        "Ocp-Apim-Subscription-Key": self.key,
                        "Ocp-Apim-Subscription-Region": self.region,
                        "Content-Type": "application/json",
                    },
                    json=[{"text": text}],
                    timeout=10.0,
                )
                response.raise_for_status()
                result = response.json()
                return result[0]["language"]
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return "en"
