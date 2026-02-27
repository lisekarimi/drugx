# src/clients/ddinter.py
"""DDInter client for drug interaction checking using PostgreSQL database.

Provides functionality to check interactions between normalized drug ingredients.
"""

from typing import Any

from ..constants import ATC_CATEGORIES
from ..utils.database import get_db_pool, init_failed_lookups_table, setup_database
from ..utils.log_failed_drug import log_failed_drug
from ..utils.logging import logger
from .pubchem import get_synonyms as get_pubchem_synonyms


class InteractionNotFoundError(Exception):
    """Raised when no interaction is found between two drugs."""

    def __init__(self, ingredient_a: str, ingredient_b: str):
        """Initialize with drug ingredient names."""
        self.ingredient_a = ingredient_a
        self.ingredient_b = ingredient_b
        super().__init__(
            f"No interaction found between '{ingredient_a}' and '{ingredient_b}'"
        )


class DDInterDatabaseError(Exception):
    """Raised when DDInter database operation fails."""

    pass


class DDInterClient:
    """Client for checking drug interactions using DDInter database."""

    def __init__(self):
        """Initialize the DDInter client."""
        self.pool = None

    async def __aenter__(self):
        """Enter the async context manager."""
        await self._ensure_database_ready()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the async context manager."""
        if self.pool:
            await self.pool.close()

    async def _ensure_database_ready(self):
        """Ensure database is set up and connection pool is available."""
        if self.pool is None:
            try:
                self.pool = await get_db_pool()

                # Check if table exists and has data
                async with self.pool.acquire() as conn:
                    try:
                        count = await conn.fetchval("SELECT COUNT(*) FROM ddinter")
                        if count > 0:
                            logger.info(
                                f"DDInter database ready with {count} interactions"
                            )
                            await init_failed_lookups_table(self.pool)
                            return  # Database already has data, skip setup
                    except Exception as e:
                        # Table doesn't exist or other database error
                        logger.debug(f"Table check failed: {e}")
                        pass

                # Only setup database if empty or doesn't exist
                logger.info("Setting up empty DDInter database...")
                await self.pool.close()
                self.pool = None
                await setup_database()
                self.pool = await get_db_pool()

            except Exception as e:
                if self.pool:
                    await self.pool.close()
                    self.pool = None
                logger.error(f"Failed to connect to database: {e}")
                raise DDInterDatabaseError(f"Database connection failed: {e}") from e

    async def check_interaction(
        self, ingredient_a: str, ingredient_b: str
    ) -> dict[str, Any]:
        """Check for drug interaction between two ingredients with PubChem fallback."""
        logger.info(f"\n{'=' * 50}")
        logger.info(f"Checking: {ingredient_a} + {ingredient_b}")
        logger.info(f"{'=' * 50}")

        try:
            async with self.pool.acquire() as conn:
                # Query for bidirectional interaction
                query = """
                    SELECT *
                    FROM ddinter
                    WHERE (lower(drug_a) LIKE lower('%' || $1 || '%') AND lower(drug_b) LIKE lower('%' || $2 || '%'))
                    OR (lower(drug_a) LIKE lower('%' || $2 || '%') AND lower(drug_b) LIKE lower('%' || $1 || '%'))
                    LIMIT 1;
                """

                row = await conn.fetchrow(query, ingredient_a, ingredient_b)

                if not row:
                    # Try PubChem synonyms before giving up
                    logger.info("No direct match found, trying PubChem synonyms...")

                    # Get synonyms for both drugs
                    synonyms_a = await get_pubchem_synonyms(ingredient_a)
                    synonyms_b = await get_pubchem_synonyms(ingredient_b)

                    # Try all combinations
                    for syn_a in synonyms_a:
                        for syn_b in synonyms_b:
                            syn_row = await conn.fetchrow(query, syn_a, syn_b)
                            if syn_row:
                                logger.info(
                                    f"Found interaction via synonyms: {syn_a} + {syn_b}"
                                )
                                syn_categories = (
                                    syn_row["categories"].split(",")
                                    if syn_row["categories"]
                                    else []
                                )
                                return {
                                    "severity": syn_row["severity"],
                                    "drugs": [syn_row["drug_a"], syn_row["drug_b"]],
                                    "_categories": syn_categories,
                                }

                    # All attempts failed
                    await log_failed_drug(
                        [ingredient_a, ingredient_b], "ddinter_pubchem"
                    )
                    raise InteractionNotFoundError(ingredient_a, ingredient_b)

                # Direct match found
                categories = row["categories"].split(",") if row["categories"] else []
                result = {
                    "severity": row["severity"],
                    "drugs": [row["drug_a"], row["drug_b"]],
                    "_categories": categories,
                }

                logger.info(
                    f"Found {row['severity']} interaction: {ingredient_a} + {ingredient_b}"
                )
                return result

        except InteractionNotFoundError:
            raise  # Let get_interaction_summary handle the response
        except Exception as e:
            logger.error(f"Database query failed: {e}")
            raise DDInterDatabaseError(f"Failed to check interaction: {e}") from e

    async def get_interaction_summary(
        self, ingredient_a: str, ingredient_b: str
    ) -> dict[str, Any]:
        """Get interaction summary with category explanations for LLM."""
        try:
            interaction = await self.check_interaction(ingredient_a, ingredient_b)

            # Add category explanations for interactions found
            category_explanations = {}
            for cat in interaction.get("_categories", []):
                if cat in ATC_CATEGORIES:
                    category_explanations[cat] = ATC_CATEGORIES[cat]

            # Remove internal _categories field and add explanations
            interaction.pop("_categories", None)

            return {
                **interaction,
                "category_explanations": category_explanations,
            }

        except InteractionNotFoundError:
            # Log the failure and return minimal response for LLM
            logger.info(
                f"No interaction found between '{ingredient_a}' and '{ingredient_b}'"
            )
            await log_failed_drug(
                [ingredient_a, ingredient_b], "ddinter_no_interaction"
            )

            return {
                "drugs": [ingredient_a, ingredient_b],
                "note": "DDInter reports no known clinically significant interactions between these drugs. This doesn’t guarantee safety—only that no interaction has been established in current data.",
            }


async def check_drug_interactions_consolidated(
    ingredients: list[str],
) -> dict[str, Any]:
    """Check interactions between all pairs of drugs and return consolidated JSON."""
    interactions = []
    async with DDInterClient() as client:
        for i in range(len(ingredients)):
            for j in range(i + 1, len(ingredients)):
                result = await client.get_interaction_summary(
                    ingredients[i], ingredients[j]
                )
                interactions.append(result)

    logger.info(f"Found {len(interactions)} total interactions")
    return {"Drug-Drug interactions": interactions}
