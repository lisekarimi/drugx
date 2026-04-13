# src/clients/llm.py
"""LLM client for drug interaction analysis with Cerebras."""

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
    CEREBRAS_API_KEY,
    CEREBRAS_BASE_URL,
    CEREBRAS_MODEL,
    LLM_MAX_TOKENS,
    LLM_SYSTEM_PROMPT,
    LLM_TEMPERATURE,
    LLM_USER_PROMPT_TEMPLATE,
)
from ..utils.logging import logger


class LLMAnalysisError(Exception):
    """Raised when LLM analysis fails."""

    def __init__(self, message: str, provider: str = None):
        """Initialize with error message and optional provider."""
        self.provider = provider
        super().__init__(message)


class LLMClient:
    """Client for drug interaction analysis using Cerebras."""

    def __init__(self):
        """Initialize the LLM client with API keys from constants."""
        if CEREBRAS_API_KEY:
            self.openai_client = openai.AsyncOpenAI(
                api_key=CEREBRAS_API_KEY,
                base_url=CEREBRAS_BASE_URL,
            )
        else:
            self.openai_client = None
            logger.warning("CEREBRAS_API_KEY not found in environment")

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
        """Call Cerebras for drug interaction analysis."""
        if not self.openai_client:
            raise LLMAnalysisError("Cerebras API key not provided", "cerebras")

        logger.info("Calling Cerebras for drug interaction analysis...")

        try:
            response = await self.openai_client.chat.completions.create(
                model=CEREBRAS_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": LLM_SYSTEM_PROMPT,
                    },
                    {"role": "user", "content": prompt},
                ],
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                reasoning_effort="low",
            )

            content = response.choices[0].message.content
            logger.info("Cerebras analysis completed successfully")
            return content

        except openai.APIError as e:
            logger.error(f"Cerebras API error: {e}")
            raise LLMAnalysisError(f"Cerebras API failed: {e}", "cerebras") from e
        except Exception as e:
            logger.error(f"Cerebras request failed: {e}")
            raise LLMAnalysisError(f"Cerebras request failed: {e}", "cerebras") from e

    async def analyze_drug_interactions(
        self, rxnorm_json: dict, ddinter_json: dict, openfda_json: dict
    ) -> dict[str, Any]:
        """Analyze drug interactions using Cerebras."""
        prompt = self._create_analysis_prompt(rxnorm_json, ddinter_json, openfda_json)

        if not self.openai_client:
            raise LLMAnalysisError("Cerebras API key not provided", "cerebras")

        try:
            analysis = await self._call_openai_gpt4(prompt)
            return {
                "analysis": analysis,
                "provider": "cerebras",
                "status": "success",
            }
        except LLMAnalysisError as e:
            logger.error(f"Cerebras analysis failed: {e}")
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
