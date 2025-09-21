# src/clients/pubchem.py
"""PubChem API client for drug synonym expansion and fallback identification."""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..constants import PROJECT_NAME, VERSION
from ..utils.logging import logger
from ..utils.text_cleaning import clean_drug_name


class PubChemAPIError(Exception):
    """Raised when PubChem API returns an error."""

    pass


class PubChemClient:
    """Client for interacting with the PubChem REST API."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self):
        """Initialize the PubChem client with an HTTP session."""
        self.session = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "User-Agent": f"{PROJECT_NAME}/{VERSION}",
                "Accept": "application/json",
            },
        )

    async def __aenter__(self):
        """Enter the async context manager."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        await self.session.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=8),
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
    )
    async def _make_request(self, endpoint: str) -> dict[str, Any]:
        """Make a request to the PubChem API with retry logic."""
        url = f"{self.BASE_URL}/{endpoint}"
        # logger.debug(f"Making PubChem API request: {url}")

        try:
            response = await self.session.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"PubChem API request failed: {e}")
            raise PubChemAPIError(f"PubChem API error: {e}") from e

    async def get_synonyms(self, drug_name: str) -> list[str]:
        """Get first 3 synonyms for a drug name from PubChem."""
        logger.info(f"Getting PubChem synonyms for: '{drug_name}'")

        try:
            # URL encode the drug name
            encoded_name = drug_name.replace(" ", "%20")
            endpoint = f"compound/name/{encoded_name}/synonyms/JSON"

            data = await self._make_request(endpoint)

            # Check for PubChem fault response
            if "Fault" in data:
                logger.warning(
                    f"PubChem could not find compound: '{drug_name}' - {data['Fault']['Message']}"
                )
                return []

            # Extract synonyms from response
            info_list = data.get("InformationList", {})
            information = info_list.get("Information", [])

            # Get first 3 synonyms
            synonyms = information[0].get("Synonym", [])

            # Clean synonyms - keep only letters and spaces, remove empty strings
            cleaned_synonyms = []
            for syn in synonyms[:3]:
                cleaned = clean_drug_name(syn)
                if cleaned:  # Only add non-empty strings
                    cleaned_synonyms.append(cleaned)

            logger.info(
                f"Found {len(synonyms)} total synonyms, returning {len(cleaned_synonyms)} cleaned for '{drug_name}': {cleaned_synonyms}"
            )
            return cleaned_synonyms[:3]

        except PubChemAPIError:
            return []
        except Exception as e:
            logger.error(f"Error getting PubChem synonyms for '{drug_name}': {e}")
            return []


async def get_synonyms(drug_name: str) -> list[str]:
    """Get first 3 synonyms for a drug name from PubChem."""
    async with PubChemClient() as client:
        return await client.get_synonyms(drug_name)
