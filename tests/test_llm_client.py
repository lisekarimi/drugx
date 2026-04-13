# tests/test_llm_client.py
from unittest.mock import patch

import pytest

from src.clients.llm import (
    LLMAnalysisError,
    LLMClient,
    analyze_drug_interactions_safe,
)

# Simple mock data
SAMPLE_DATA = {
    "rxnorm": {"normalized_drugs": [{"rxcui": "1191", "in": "aspirin"}]},
    "ddinter": {"Drug-Drug interactions": [{"severity": "Major"}]},
    "openfda": {"adverse_events": {"n_reports": 100}},
}


class TestLLMClient:
    """Simple tests for LLMClient main functionality."""

    async def test_initialization_with_keys(self):
        """Test client initialization with API keys."""
        with patch("src.clients.llm.OPENAI_API_KEY", "test-key"):
            client = LLMClient()
            assert client.openai_client is not None

    async def test_initialization_without_keys(self):
        """Test client initialization without API keys."""
        with patch("src.clients.llm.OPENAI_API_KEY", None):
            client = LLMClient()
            assert client.openai_client is None

    async def test_create_analysis_prompt(self):
        """Test prompt creation from input data."""
        with patch("src.clients.llm.OPENAI_API_KEY", "test-key"):
            client = LLMClient()
            prompt = client._create_analysis_prompt(
                SAMPLE_DATA["rxnorm"], SAMPLE_DATA["ddinter"], SAMPLE_DATA["openfda"]
            )

            assert "aspirin" in prompt
            assert "Major" in prompt

    @patch("src.clients.llm.LLMClient._call_openai_gpt4")
    async def test_analyze_success_openai(self, mock_openai):
        """Test successful analysis with OpenAI."""
        mock_openai.return_value = "Analysis result"

        with patch("src.clients.llm.OPENAI_API_KEY", "test-key"):
            client = LLMClient()
            result = await client.analyze_drug_interactions(
                SAMPLE_DATA["rxnorm"], SAMPLE_DATA["ddinter"], SAMPLE_DATA["openfda"]
            )

        assert result["provider"] == "openai"
        assert result["status"] == "success"
        assert result["analysis"] == "Analysis result"

    async def test_call_openai_no_client(self):
        """Test OpenAI call without client."""
        with patch("src.clients.llm.OPENAI_API_KEY", None):
            client = LLMClient()

            with pytest.raises(LLMAnalysisError) as exc_info:
                await client._call_openai_gpt4("test prompt")

            assert exc_info.value.provider == "openai"
            assert "API key not provided" in str(exc_info.value)


class TestConvenienceFunctions:
    """Test the convenience function."""

    @patch("src.clients.llm.LLMClient.analyze_drug_interactions")
    async def test_analyze_drug_interactions_safe_success(self, mock_analyze):
        """Test successful safe analysis."""
        mock_analyze.return_value = {
            "analysis": "Test analysis",
            "provider": "openai",
            "status": "success",
        }

        result = await analyze_drug_interactions_safe(
            SAMPLE_DATA["rxnorm"], SAMPLE_DATA["ddinter"], SAMPLE_DATA["openfda"]
        )

        assert result["provider"] == "openai"
        assert result["status"] == "success"


class TestErrorHandling:
    """Test error handling."""

    async def test_llm_analysis_error_with_provider(self):
        """Test LLMAnalysisError with provider."""
        error = LLMAnalysisError("Test error", "openai")

        assert error.provider == "openai"
        assert "Test error" in str(error)

    async def test_llm_analysis_error_without_provider(self):
        """Test LLMAnalysisError without provider."""
        error = LLMAnalysisError("Test error")

        assert error.provider is None
        assert "Test error" in str(error)
