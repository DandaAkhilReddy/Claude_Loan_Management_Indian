"""Tests for AI insights routes (/api/ai/*)."""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


# ---------------------------------------------------------------------------
# explain-loan
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestExplainLoan:
    async def test_explain_loan_success(self, async_client, mock_loan):
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_loan)

        mock_ai = MagicMock()
        mock_ai.explain_loan = AsyncMock(return_value="This is a home loan explanation.")

        with (
            patch("app.api.routes.ai_insights.LoanRepository", return_value=mock_repo),
            patch("app.api.routes.ai_insights.AIService", return_value=mock_ai),
        ):
            resp = await async_client.post("/api/ai/explain-loan", json={
                "loan_id": str(mock_loan.id),
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "This is a home loan explanation."
        assert data["language"] == "en"

    async def test_explain_loan_not_found(self, async_client):
        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=None)

        with patch("app.api.routes.ai_insights.LoanRepository", return_value=mock_repo):
            resp = await async_client.post("/api/ai/explain-loan", json={
                "loan_id": "00000000-0000-4000-a000-000000000099",
            })

        assert resp.status_code == 404

    async def test_explain_loan_translates_for_hindi_user(self, async_client, mock_user, mock_loan):
        mock_user.preferred_language = "hi"

        mock_repo = MagicMock()
        mock_repo.get_by_id = AsyncMock(return_value=mock_loan)

        mock_ai = MagicMock()
        mock_ai.explain_loan = AsyncMock(return_value="English explanation")

        mock_translator = MagicMock()
        mock_translator.translate = AsyncMock(return_value="Hindi explanation")

        with (
            patch("app.api.routes.ai_insights.LoanRepository", return_value=mock_repo),
            patch("app.api.routes.ai_insights.AIService", return_value=mock_ai),
            patch("app.api.routes.ai_insights.TranslatorService", return_value=mock_translator),
        ):
            resp = await async_client.post("/api/ai/explain-loan", json={
                "loan_id": str(mock_loan.id),
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["text"] == "Hindi explanation"
        assert data["language"] == "hi"
        mock_translator.translate.assert_called_once_with("English explanation", "hi")

        # Reset for other tests
        mock_user.preferred_language = "en"


# ---------------------------------------------------------------------------
# explain-strategy
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestExplainStrategy:
    async def test_explain_strategy_success(self, async_client):
        mock_ai = MagicMock()
        mock_ai.explain_strategy = AsyncMock(return_value="Avalanche pays least interest.")

        with patch("app.api.routes.ai_insights.AIService", return_value=mock_ai):
            resp = await async_client.post("/api/ai/explain-strategy", json={
                "strategy_name": "avalanche",
                "num_loans": 3,
                "extra": 10000.0,
                "interest_saved": 245000.0,
                "months_saved": 18,
                "payoff_order": ["HDFC Personal", "SBI Home", "Axis Car"],
            })

        assert resp.status_code == 200
        assert resp.json()["text"] == "Avalanche pays least interest."


# ---------------------------------------------------------------------------
# ask (RAG Q&A)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestAsk:
    async def test_ask_success(self, async_client):
        mock_embed_svc = MagicMock()
        mock_embed_svc.generate_embedding = AsyncMock(return_value=[0.1] * 1536)

        mock_result = MagicMock()
        mock_result.chunk_text = "RBI says 0% penalty on floating rate."

        mock_embed_repo = MagicMock()
        mock_embed_repo.similarity_search = AsyncMock(return_value=[mock_result])

        mock_ai = MagicMock()
        mock_ai.ask_with_context = AsyncMock(return_value="No penalty for floating rate prepayment.")

        with (
            patch("app.api.routes.ai_insights.EmbeddingService", return_value=mock_embed_svc),
            patch("app.api.routes.ai_insights.EmbeddingRepository", return_value=mock_embed_repo),
            patch("app.api.routes.ai_insights.AIService", return_value=mock_ai),
        ):
            resp = await async_client.post("/api/ai/ask", json={
                "question": "What is RBI rule on prepayment?",
            })

        assert resp.status_code == 200
        assert "floating" in resp.json()["text"].lower()


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
class TestTTS:
    async def test_tts_english(self, async_client):
        mock_tts = MagicMock()
        mock_tts.generate_audio = AsyncMock(return_value="base64audiodata==")

        with patch("app.api.routes.ai_insights.TTSService", return_value=mock_tts):
            resp = await async_client.post("/api/ai/tts", json={
                "text": "Hello world",
                "language": "en",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_base64"] == "base64audiodata=="
        assert data["language"] == "en"

    async def test_tts_hindi(self, async_client):
        mock_tts = MagicMock()
        mock_tts.generate_audio = AsyncMock(return_value="hindiAudio==")

        with patch("app.api.routes.ai_insights.TTSService", return_value=mock_tts):
            resp = await async_client.post("/api/ai/tts", json={
                "text": "Namaste",
                "language": "hi",
            })

        assert resp.status_code == 200
        assert resp.json()["language"] == "hi"

    async def test_tts_null_audio(self, async_client):
        mock_tts = MagicMock()
        mock_tts.generate_audio = AsyncMock(return_value=None)

        with patch("app.api.routes.ai_insights.TTSService", return_value=mock_tts):
            resp = await async_client.post("/api/ai/tts", json={
                "text": "Hello",
                "language": "en",
            })

        assert resp.status_code == 200
        assert resp.json()["audio_base64"] is None
