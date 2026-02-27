# src/clients/openfda.py
"""OpenFDA client for adverse event statistics from FAERS database.

Provides functionality to get adverse event context for drug combinations.
This data is for contextual information only, not authoritative interaction data.
"""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..constants import OPENFDA_BASE_URL, PROJECT_NAME, VERSION
from ..utils.log_failed_drug import log_failed_drug
from ..utils.logging import logger
from .pubchem import get_synonyms as get_pubchem_synonyms


class OpenFDAError(Exception):
    """Raised when OpenFDA API returns an error."""

    def __init__(self, message: str, status_code: int = None):
        """Initialize with error message and optional status code."""
        self.status_code = status_code
        super().__init__(message)


class OpenFDAClient:
    """Client for OpenFDA adverse event data (FAERS database)."""

    BASE_URL = OPENFDA_BASE_URL

    def __init__(self):
        """Initialize the OpenFDA client with an HTTP session."""
        # Create HTTP client with reasonable timeout and proper headers
        self.session = httpx.AsyncClient(
            # 30 second timeout handles slow OpenFDA responses
            timeout=30.0,
            headers={
                # Identify our application to the API server
                "User-Agent": f"{PROJECT_NAME}/{VERSION}",
                # Request JSON responses from the API
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
    async def get_adverse_events(self, ingredient_names: list[str]) -> dict[str, Any]:
        """Get adverse events involving multiple drugs with PubChem fallback."""
        if not ingredient_names:
            return {"drugs": [], "n_reports": 0, "n_serious": 0}

        if len(ingredient_names) < 2:
            return {"drugs": ingredient_names, "n_reports": 0, "n_serious": 0}

        # Build query for multiple drugs - preserve original case
        drug_terms = [
            f'patient.drug.medicinalproduct:"{drug}"' for drug in ingredient_names
        ]
        search_query = "+AND+".join(drug_terms)

        params = {
            "search": search_query,
            "limit": 100,  # Get sample of reports for analysis
        }

        url = f"{self.BASE_URL}/drug/event.json"
        logger.info(
            f"OpenFDA query for {'+'.join(ingredient_names)}: {len(ingredient_names)} drugs"
        )

        try:
            url = f"{url}?search={search_query}&limit={params['limit']}"
            response = await self.session.get(url)
            response.raise_for_status()
            data = response.json()

            result = self._process_adverse_events(data, ingredient_names)
            if result["n_reports"] > 0:
                return result

            # No reports found, try PubChem synonyms
            logger.info("No OpenFDA reports found, trying PubChem synonyms...")
            return await self._try_pubchem_fallback(ingredient_names)

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # No adverse events found - try PubChem fallback
                logger.info(f"No FAERS reports found for {'+'.join(ingredient_names)}")
                return await self._try_pubchem_fallback(ingredient_names)
            else:
                logger.error(f"OpenFDA API error {e.response.status_code}: {e}")
                raise OpenFDAError(
                    f"OpenFDA API failed: HTTP {e.response.status_code}",
                    e.response.status_code,
                ) from e

        except httpx.HTTPError as e:
            logger.error(f"OpenFDA connection error: {e}")
            raise OpenFDAError(f"OpenFDA connection failed: {e}") from e

    async def _try_pubchem_fallback(
        self, ingredient_names: list[str]
    ) -> dict[str, Any]:
        """Try PubChem synonyms for adverse event lookup."""
        # Get synonyms for all drugs
        all_synonyms = []
        for drug in ingredient_names:
            synonyms = await get_pubchem_synonyms(drug)
            all_synonyms.append(synonyms if synonyms else [drug])

        # Try combinations (limit to avoid explosion)
        import itertools

        for combo in itertools.product(*all_synonyms):
            try:
                # Build query for synonym combination
                drug_terms = [
                    f'patient.drug.medicinalproduct:"{drug}"' for drug in combo
                ]
                search_query = "+AND+".join(drug_terms)
                url = f"{self.BASE_URL}/drug/event.json?search={search_query}&limit=100"

                response = await self.session.get(url)
                response.raise_for_status()
                data = response.json()

                result = self._process_adverse_events(data, list(combo))
                if result["n_reports"] > 0:
                    logger.info(
                        f"Found OpenFDA reports via synonyms: {' + '.join(combo)}"
                    )
                    return result

            except (httpx.HTTPError, OpenFDAError):
                continue

        # All attempts failed - log and return empty result
        await log_failed_drug(ingredient_names, "openfda_no_reports")
        return {
            "drugs": ingredient_names,
            "n_reports": 0,
            "n_serious": 0,
            "top_reactions": [],
            "last_report_date": None,
            "sample_size": 0,
            "reason": "No reports found after synonym search",
        }

    def _process_adverse_events(self, data: dict, drugs: list[str]) -> dict[str, Any]:
        """Process OpenFDA adverse event response into structured context data."""
        # Extract total count from meta
        meta = data.get("meta", {})
        results_meta = meta.get("results", {})
        total_reports = results_meta.get("total", 0)

        # Get actual results returned for analysis
        results = data.get("results", [])
        sample_size = len(results)

        serious_count = 0
        recent_reactions = []
        latest_date = None

        # Process individual reports from sample
        for result in results:
            # Count serious events - handle both string "1" and integer 1
            serious_flag = result.get("serious")
            if serious_flag == "1" or serious_flag == 1:
                serious_count += 1

            # Collect reaction types (MedDRA terms)
            patient = result.get("patient", {})
            reactions = patient.get("reaction", [])

            for reaction in reactions:
                reaction_term = reaction.get("reactionmeddrapt")
                if (
                    reaction_term
                    and reaction_term not in recent_reactions
                    and len(recent_reactions) < 10
                ):
                    recent_reactions.append(reaction_term)

            # Track most recent report date
            receive_date = result.get("receivedate")
            if receive_date and (not latest_date or receive_date > latest_date):
                latest_date = receive_date

        # Format latest date for readability (YYYYMMDD -> YYYY-MM-DD)
        formatted_date = None
        if latest_date and len(latest_date) == 8:
            formatted_date = f"{latest_date[:4]}-{latest_date[4:6]}-{latest_date[6:8]}"

        result = {
            "drugs": drugs,
            "n_reports": total_reports,  # Total from meta (authoritative)
            "n_serious": serious_count,  # From sample only
            "top_reactions": recent_reactions[:5],  # From sample only
            "last_report_date": formatted_date,
            "sample_size": sample_size,  # Make sampling transparent
        }

        logger.info(
            f"Found {total_reports} total FAERS reports for {'+'.join(drugs)} (analyzed {sample_size} reports: {serious_count} serious)"
        )

        return result


# Convenience functions
async def get_adverse_event_context_safe(ingredient_names: list[str]) -> dict[str, Any]:
    """Safely get adverse event context, never raises exceptions."""
    try:
        async with OpenFDAClient() as client:
            return {"adverse_events": await client.get_adverse_events(ingredient_names)}
    except Exception as e:
        logger.error(f"OpenFDA context failed: {e}")
        await log_failed_drug(ingredient_names, "openfda_error")
        return {
            "adverse_events": {
                "drugs": ingredient_names,
                "n_reports": 0,
                "n_serious": 0,
                "top_reactions": [],
                "last_report_date": None,
                "sample_size": 0,
                "error": f"OpenFDA failed: {str(e)}",
            }
        }
