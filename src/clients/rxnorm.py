# src/clients/rxnorm.py
"""RxNorm API client for drug name normalization.

Provides functionality to get RxCUI, ingredient names, and drug classes.
"""

import re
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ..constants import PROJECT_NAME, RXNORM_BASE_URL, VERSION
from ..utils.log_failed_drug import log_failed_drug
from ..utils.logging import logger
from .pubchem import get_synonyms as get_pubchem_synonyms


class DrugNotFoundError(Exception):
    """Raised when a drug is not found in RxNorm database."""

    def __init__(self, drug_name: str, candidates: list[str] = None):
        """Initialize with drug name and optional candidates."""
        self.drug_name = drug_name
        # Store candidates for programmatic access, defaulting to empty list
        self.candidates = candidates or []
        # Create different error messages depending on whether we have suggestions
        if self.candidates:
            super().__init__(
                f"Drug '{drug_name}' not found in RxNorm database. Candidates: {candidates}"
            )
        else:
            super().__init__(f"Drug '{drug_name}' not found in RxNorm database")


class RxNormAPIError(Exception):
    """Raised when RxNorm API returns an error."""

    pass


class RxNormClient:
    """Client for interacting with the RxNorm REST API."""

    BASE_URL = RXNORM_BASE_URL

    def __init__(self):
        """Initialize the RxNorm client with an HTTP session."""
        # Create HTTP client with reasonable timeout and proper headers
        self.session = httpx.AsyncClient(
            # 30 second timeout handles slow RxNorm responses
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
        # Called when entering 'async with' block - just return self
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        # Called when exiting 'async with' block - clean up HTTP session
        await self.session.aclose()

    @retry(
        # Try up to 3 times before giving up
        stop=stop_after_attempt(3),
        # Wait with exponential backoff: 4s, 8s, 10s (capped at max)
        wait=wait_exponential(multiplier=1, min=4, max=10),
        # Only retry on transient network errors, not HTTP 4xx/5xx responses
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
    )
    async def _make_request(
        self, endpoint: str, params: dict[str, Any] = None
    ) -> dict[str, Any]:
        """Make a request to the RxNorm API with retry logic."""
        # Construct full URL from base URL and endpoint
        url = f"{self.BASE_URL}/{endpoint}"

        try:
            # Make HTTP GET request with query parameters
            response = await self.session.get(url, params=params)
            # Raise exception for HTTP error status codes (4xx, 5xx)
            response.raise_for_status()
            # Parse JSON response and return as dictionary
            data = response.json()
            return data
        except httpx.HTTPError as e:
            # Log the error for debugging
            logger.error(f"RxNorm API request failed: {e}")
            # Convert HTTP errors to our custom exception type for consistent error handling
            raise RxNormAPIError(f"{url}: {e}") from e

    async def get_rxcui(self, drug_name: str) -> str:
        """Get RxCUI for a drug name with PubChem fallback. Raises DrugNotFoundError if not found."""
        try:
            # Try exact search first
            data = await self._make_request(
                "rxcui.json", params={"name": drug_name, "search": "2"}
            )

            # Extract RxCUI from response
            id_group = data.get("idGroup", {})
            rxnorm_ids = id_group.get("rxnormId", [])

            if rxnorm_ids:
                rxcui = rxnorm_ids[0]
                return rxcui

            # Fallback to approximate search
            logger.info(
                f"No exact match for '{drug_name}', trying approximate search..."
            )
            approx_data = await self._make_request(
                "approximateTerm.json",
                params={"term": drug_name, "maxEntries": "5"},  # Get more candidates
            )

            # Extract approximate matches
            approx_group = approx_data.get("approximateGroup", {})
            candidates = approx_group.get("candidate", [])

            if candidates:
                # Sort by highest score, lowest rank to get best match
                candidates.sort(
                    key=lambda c: (-float(c.get("score", 0)), int(c.get("rank", 1)))
                )
                best_candidate = candidates[0]
                rxcui = best_candidate.get("rxcui")
                matched_term = best_candidate.get("name")

                # If best candidate has a direct RxCUI, use it immediately
                if (
                    rxcui
                    and matched_term
                    and matched_term.lower() not in ["none", "null"]
                ):
                    logger.warning(
                        f"Using approximate match: '{drug_name}' → '{matched_term}' (RxCUI: {rxcui})"
                    )
                    return rxcui

                # No direct RxCUI — retry exact search with all valid candidate names
                candidate_names = [
                    c.get("name")
                    for c in candidates
                    if c.get("name") and c.get("name").lower() not in ["none", "null"]
                ]
                for candidate_name in candidate_names[:3]:
                    try:
                        candidate_data = await self._make_request(
                            "rxcui.json", params={"name": candidate_name, "search": "2"}
                        )
                        candidate_id_group = candidate_data.get("idGroup", {})
                        candidate_rxnorm_ids = candidate_id_group.get("rxnormId", [])
                        if candidate_rxnorm_ids:
                            rxcui = candidate_rxnorm_ids[0]
                            logger.info(
                                f"Found RxCUI via candidate: '{drug_name}' → '{candidate_name}' (RxCUI: {rxcui})"
                            )
                            return rxcui
                    except (RxNormAPIError, DrugNotFoundError):
                        continue

            # Try RxNorm spelling suggestions
            logger.info(f"Trying RxNorm spelling suggestions for '{drug_name}'...")
            suggestions_data = await self._make_request(
                "spellingsuggestions.json", params={"name": drug_name}
            )
            suggestion_group = suggestions_data.get("suggestionGroup", {})
            suggestion_list = suggestion_group.get("suggestionList") or {}
            suggestions = suggestion_list.get("suggestion", [])

            for suggestion in suggestions[:3]:
                try:
                    suggestion_data = await self._make_request(
                        "rxcui.json", params={"name": suggestion, "search": "2"}
                    )
                    suggestion_id_group = suggestion_data.get("idGroup", {})
                    suggestion_rxnorm_ids = suggestion_id_group.get("rxnormId", [])

                    if suggestion_rxnorm_ids:
                        rxcui = suggestion_rxnorm_ids[0]
                        logger.info(
                            f"Found RxCUI via spelling suggestion: '{drug_name}' → '{suggestion}' (RxCUI: {rxcui})"
                        )
                        return rxcui
                except (RxNormAPIError, DrugNotFoundError):
                    continue

            # Try PubChem synonyms fallback
            logger.info(f"RxNorm failed for '{drug_name}', trying PubChem synonyms...")
            synonyms = await get_pubchem_synonyms(drug_name)

            for synonym in synonyms:
                try:
                    # Recursive call with synonym
                    synonym_data = await self._make_request(
                        "rxcui.json", params={"name": synonym, "search": "2"}
                    )
                    synonym_id_group = synonym_data.get("idGroup", {})
                    synonym_rxnorm_ids = synonym_id_group.get("rxnormId", [])

                    if synonym_rxnorm_ids:
                        rxcui = synonym_rxnorm_ids[0]
                        logger.info(
                            f"Found RxCUI via PubChem synonym: '{synonym}' → {rxcui}"
                        )
                        return rxcui
                except (RxNormAPIError, DrugNotFoundError):
                    continue

            # If all attempts fail, log and raise
            await log_failed_drug([drug_name], "rxnorm_pubchem")
            raise DrugNotFoundError(drug_name)

        except DrugNotFoundError:
            raise

    async def get_drug_info(self, rxcui: str) -> dict[str, Any]:
        """Get ingredient name and drug classes for an RxCUI."""
        try:
            # Get ingredient name
            ing_data = await self._make_request(
                f"rxcui/{rxcui}/related.json", params={"tty": "IN"}
            )

            ingredient_name = None
            related_group = ing_data.get("relatedGroup", {})
            concept_group = related_group.get("conceptGroup", [])

            for group in concept_group:
                if group.get("tty") == "IN":
                    concept_properties = group.get("conceptProperties", [])
                    if concept_properties:
                        ingredient_name = concept_properties[0].get("name")
                        break

            # Fallback: if no IN found, get drug name and clean it
            if not ingredient_name:
                logger.info(f"No IN found for RxCUI {rxcui}, using fallback...")
                drug_data = await self._make_request(f"rxcui/{rxcui}.json")

                id_group = drug_data.get("idGroup", {})
                rxnorm_ids = id_group.get("rxnormId", [])

                if rxnorm_ids:
                    # Get the drug name directly from idGroup
                    raw_name = id_group.get("name", "").lower()
                    if raw_name:
                        # Clean the name
                        SALT_SUFFIXES = r"(sodium|hydrochloride|sulfate|tartrate|citrate|phosphate|acetate|chloride|maleate|succinate|fumarate|lactate|hcl|er|sr|xl|cr)"
                        ingredient_name = re.sub(
                            rf"(\s|-){SALT_SUFFIXES}$",
                            "",
                            raw_name.strip(),
                            flags=re.IGNORECASE,
                        ).strip()

                        logger.info(
                            f"Cleaned ingredient name: '{raw_name}' → '{ingredient_name}'"
                        )

            # Get drug classes using RxClass API
            classes = {}
            try:
                class_data = await self._make_request(
                    "rxclass/class/byRxcui.json", params={"rxcui": rxcui}
                )

                rx_class_drug_info_list = class_data.get("rxclassDrugInfoList", {})
                rx_class_drug_info = rx_class_drug_info_list.get("rxclassDrugInfo", [])

                # Group by classType - collect ATC data with classId for sorting
                atc_items = []
                for drug_info_item in rx_class_drug_info:
                    class_item = drug_info_item.get("rxclassMinConceptItem", {})
                    class_type = class_item.get("classType", "").upper()
                    class_name = class_item.get("className", "")
                    class_id = class_item.get("classId", "")

                    # Check if it's an ATC class (could be ATC1-4, ATC2, etc.)
                    is_atc = class_type.startswith("ATC")

                    if (class_type in ["EPC", "MOA", "PE"] or is_atc) and class_name:
                        # For ATC, also check relaSource and collect for sorting
                        if is_atc:
                            rela_source = drug_info_item.get("relaSource", "")
                            if rela_source in ["ATC", "ATCPROD"]:
                                atc_items.append((class_id, class_name))
                        else:
                            if class_type.lower() not in classes:
                                classes[class_type.lower()] = []
                            classes[class_type.lower()].append(class_name)

                # Process ATC items - sort by classId, then extract className
                if atc_items:
                    atc_items_sorted = sorted(
                        set(atc_items), key=lambda x: x[0]
                    )  # Sort by classId
                    classes["atc"] = [item[1] for item in atc_items_sorted]

                # Deduplicate and sort non-ATC class types
                for class_type in ["epc", "moa", "pe"]:
                    if class_type in classes:
                        classes[class_type] = sorted(list(set(classes[class_type])))

                # Ensure all class types are present (empty lists if no data)
                for class_type in ["epc", "moa", "pe", "atc"]:
                    if class_type not in classes:
                        classes[class_type] = []

            except Exception as e:
                logger.debug(f"Error getting drug classes for RxCUI {rxcui}: {e}")
                classes = {"epc": [], "moa": [], "pe": [], "atc": []}

            # Guard: fail if no ingredient name found
            if not ingredient_name:
                raise RxNormAPIError(f"No ingredient name found for RxCUI {rxcui}")

            return {"ingredient_name": ingredient_name, "classes": classes}

        except RxNormAPIError:
            # Let API errors propagate - these indicate serious issues that should fail fast
            raise
        except Exception as e:
            logger.error(f"Error getting drug info for RxCUI {rxcui}: {e}")
            return {"ingredient_name": None, "classes": {}}

    async def normalize_drug(self, drug_name: str) -> dict[str, Any]:
        """Normalize a drug name to RxCUI, ingredient name, and classes.

        Args:
            drug_name: The drug name to normalize

        Returns:
            Dict with rxcui, in (ingredient name), and classes

        Raises:
            DrugNotFoundError: If drug is not found in RxNorm (may include candidates)
            RxNormAPIError: If API request fails

        """
        try:
            # Get RxCUI - will raise DrugNotFoundError if not found
            rxcui = await self.get_rxcui(drug_name)

            # Get drug information
            drug_info = await self.get_drug_info(rxcui)

            result = {
                "rxcui": rxcui,
                "in": drug_info["ingredient_name"].strip()
                if drug_info["ingredient_name"]
                else None,
                "classes": drug_info["classes"],
            }
            return result

        except DrugNotFoundError as e:
            result = {
                "rxcui": None,
                "in": None,
                "classes": {"epc": [], "moa": [], "pe": [], "atc": []},
                "error": str(e),
                "candidates": e.candidates,
            }
            return result


async def normalize_drug_safe(drug_name: str) -> dict[str, Any]:
    """Safely normalize a drug name, returning candidates if not found.

    Args:
        drug_name: The drug name to normalize

    Returns:
        Dict with either normalized data or candidates list

    """
    # Use context manager to ensure proper cleanup of HTTP connections
    async with RxNormClient() as client:
        try:
            # Attempt normal drug normalization
            return await client.normalize_drug(drug_name)
        except DrugNotFoundError as e:
            # Handle case where drug isn't found - return candidates or error message
            if e.candidates:
                return {"candidates": e.candidates}
            else:
                return {"error": f"Drug '{drug_name}' not found"}
        except RxNormAPIError as e:
            # Handle API failures gracefully - return error message instead of crashing
            return {"error": str(e)}


async def normalize_and_deduplicate_drugs(drug_names: list[str]) -> dict[str, Any]:
    """Normalize multiple drugs and deduplicate by ingredient name.

    Args:
        drug_names: List of drug names to normalize

    Returns:
        Dict with normalized_drugs list containing unique drugs by ingredient name

    """
    normalized_drugs = []
    seen_ingredients = set()

    # Process each drug individually
    for drug_name in drug_names:
        logger.info(f"\n--- Normalizing: {drug_name} ---")
        result = await normalize_drug_safe(drug_name)

        # Only include successful normalizations
        if "rxcui" in result and result["rxcui"] and result["in"]:
            ingredient = result["in"]
            drug_json = {
                "rxcui": result["rxcui"],
                "in": result["in"],
                "classes": result["classes"],
            }

            # Skip if we've already seen this ingredient
            if ingredient not in seen_ingredients:
                seen_ingredients.add(ingredient)
                normalized_drugs.append(drug_json)
                logger.info(f"✓ Added: {ingredient}")
            else:
                logger.info(f"⚠ Duplicate: {ingredient}")
        else:
            # Log failed normalizations
            if "candidates" in result:
                logger.warning(f"Candidates for '{drug_name}': {result['candidates']}")
                await log_failed_drug([drug_name], "normalization_failed")
            elif "error" in result:
                logger.error(f"Error normalizing '{drug_name}': {result['error']}")

    final_ingredients = [drug["in"] for drug in normalized_drugs]
    logger.info(f"Final deduplicated drugs: {final_ingredients}")
    return {"normalized_drugs": normalized_drugs}
