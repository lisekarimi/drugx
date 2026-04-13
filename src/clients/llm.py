# src/clients/llm.py
"""LLM client for drug interaction analysis with GPT-4."""

import json
from typing import Any

import openai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..constants import (
    LLM_MAX_TOKENS,
    LLM_SYSTEM_PROMPT,
    LLM_TEMPERATURE,
    LLM_USER_PROMPT_TEMPLATE,
    OPENAI_API_KEY,
    OPENAI_MODEL,
)
from ..utils.logging import logger


class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""

    def __init__(self, message: str, provider: str = None):
        """Initialize with error message and optional provider."""
        self.provider = provider
        super().__init__(message)


class LLMClient:
    """Client for drug interaction analysis using OpenAI."""

    def __init__(self):
        """Initialize the LLM client with API keys from constants."""
        if OPENAI_API_KEY:
            self.openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
        else:
            self.openai_client = None
            logger.warning("OPENAI_API_KEY not found in environment")

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""

    def _create_analysis_prompt(
        self, rxnorm_json: dict, ddinter_json: dict, openfda_json: dict
    ) -> str:
        """Create the analysis prompt for drug interaction synthesis."""
        return LLM_USER_PROMPT_TEMPLATE.format(
            rxnorm_json=json.dumps(rxnorm_json, indent=2),
            ddinter_json=json.dumps(ddinter_json, indent=2),
            openfda_json=json.dumps(openfda_json, indent=2),
        )

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((openai.APITimeoutError, openai.RateLimitError)),
    )
    async def _call_openai_gpt4(self, prompt: str) -> str:
        """Call OpenAI for drug interaction analysis."""
        if not self.openai_client:
            raise LLMAnalysisError("OpenAI API key not provided", "openai")

        logger.info("Calling OpenAI for drug interaction analysis...")

        try:
            response = await self.openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": LLM_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
            )

            content = response.choices[0].message.content
            logger.info("OpenAI analysis completed successfully")
            return content

        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise LLMAnalysisError(f"OpenAI API failed: {e}", "openai") from e
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            raise LLMAnalysisError(f"OpenAI request failed: {e}", "openai") from e

    async def analyze_drug_interactions(
        self, rxnorm_json: dict, ddinter_json: dict, openfda_json: dict
    ) -> dict[str, Any]:
        """Analyze drug interactions using OpenAI."""
        prompt = self._create_analysis_prompt(rxnorm_json, ddinter_json, openfda_json)

        if not self.openai_client:
            raise LLMAnalysisError("OpenAI API key not provided", "openai")

        try:
            analysis = await self._call_openai_gpt4(prompt)
            return {
                "analysis": analysis,
                "provider": "openai",
                "status": "success",
            }
        except LLMAnalysisError as e:
            logger.error(f"OpenAI analysis failed: {e}")
            raise


# Convenience function
async def analyze_drug_interactions_safe(
    rxnorm_json: dict,
    ddinter_json: dict,
    openfda_json: dict,
) -> dict[str, Any]:
    """Safely analyze drug interactions with LLM fallback strategy."""
    try:
        async with LLMClient() as client:
            return await client.analyze_drug_interactions(
                rxnorm_json, ddinter_json, openfda_json
            )
    except Exception as e:
        logger.error(f"LLM analysis completely failed: {e}")
        raise LLMAnalysisError(f"Drug interaction analysis failed: {e}") from e
