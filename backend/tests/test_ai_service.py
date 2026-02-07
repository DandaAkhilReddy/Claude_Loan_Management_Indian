"""Tests for app.services.ai_service — Azure OpenAI GPT integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Fixture: build an AIService with client=None (not configured)
# ---------------------------------------------------------------------------


@pytest.fixture
def unconfigured_ai_service():
    """AIService with no Azure OpenAI credentials (client=None)."""
    with patch("app.services.ai_service.settings") as mock_settings:
        mock_settings.azure_openai_endpoint = ""
        mock_settings.azure_openai_key = ""
        mock_settings.azure_openai_deployment = "gpt-4o-mini"
        from app.services.ai_service import AIService

        svc = AIService()
        assert svc.client is None
        return svc


@pytest.fixture
def configured_ai_service():
    """AIService with a mocked AsyncAzureOpenAI client."""
    with patch("app.services.ai_service.settings") as mock_settings:
        mock_settings.azure_openai_endpoint = "https://fake.openai.azure.com"
        mock_settings.azure_openai_key = "fake-key"
        mock_settings.azure_openai_deployment = "gpt-4o-mini"

        with patch("app.services.ai_service.AsyncAzureOpenAI") as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value = mock_client_instance

            from app.services.ai_service import AIService

            svc = AIService()
            svc.client = mock_client_instance
            svc.deployment = "gpt-4o-mini"
            return svc


# ---------------------------------------------------------------------------
# Tests: unconfigured service returns fallback messages
# ---------------------------------------------------------------------------


class TestAIServiceNotConfigured:
    """When Azure OpenAI is not configured, all methods return a fallback."""

    @pytest.mark.asyncio
    async def test_explain_loan_not_configured(self, unconfigured_ai_service):
        result = await unconfigured_ai_service.explain_loan(
            bank_name="SBI",
            loan_type="home",
            principal=5000000,
            outstanding=4500000,
            rate=8.5,
            rate_type="floating",
            emi=43391,
            remaining_months=220,
        )
        assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_explain_strategy_not_configured(self, unconfigured_ai_service):
        result = await unconfigured_ai_service.explain_strategy(
            strategy_name="Avalanche",
            num_loans=3,
            extra=10000,
            interest_saved=250000,
            months_saved=18,
            payoff_order=["HDFC Personal", "ICICI Car", "SBI Home"],
        )
        assert "not configured" in result.lower()

    @pytest.mark.asyncio
    async def test_ask_with_context_not_configured(self, unconfigured_ai_service):
        result = await unconfigured_ai_service.ask_with_context(
            question="What is the RBI rule on prepayment?",
            context_chunks=["Some context"],
        )
        assert "not configured" in result.lower()


# ---------------------------------------------------------------------------
# Tests: configured service — error handling
# ---------------------------------------------------------------------------


class TestAIServiceErrorHandling:
    """When the Azure OpenAI client raises, the service returns an error message."""

    @pytest.mark.asyncio
    async def test_chat_error_handling(self, configured_ai_service):
        """Mock client.chat.completions.create to raise an exception."""
        configured_ai_service.client.chat.completions.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        result = await configured_ai_service.explain_loan(
            bank_name="SBI",
            loan_type="home",
            principal=5000000,
            outstanding=4500000,
            rate=8.5,
            rate_type="floating",
            emi=43391,
            remaining_months=220,
        )
        assert "couldn't generate" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_chat_success(self, configured_ai_service):
        """A successful chat completion returns the model content."""
        mock_choice = MagicMock()
        mock_choice.message.content = "Your SBI home loan explanation..."
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        configured_ai_service.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await configured_ai_service.explain_loan(
            bank_name="SBI",
            loan_type="home",
            principal=5000000,
            outstanding=4500000,
            rate=8.5,
            rate_type="floating",
            emi=43391,
            remaining_months=220,
        )
        assert result == "Your SBI home loan explanation..."

    @pytest.mark.asyncio
    async def test_chat_empty_content(self, configured_ai_service):
        """If the model returns None content, result should be empty string."""
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        configured_ai_service.client.chat.completions.create = AsyncMock(
            return_value=mock_response
        )

        result = await configured_ai_service.explain_loan(
            bank_name="SBI",
            loan_type="home",
            principal=5000000,
            outstanding=4500000,
            rate=8.5,
            rate_type="floating",
            emi=43391,
            remaining_months=220,
        )
        assert result == ""
