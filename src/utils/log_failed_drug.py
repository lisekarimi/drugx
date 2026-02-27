# src/utils/log_failed_drug.py
"""Log failed drug lookup notifications."""

import os
from datetime import UTC, datetime

import httpx

from .database import get_db_pool, init_failed_lookups_table
from .logging import logger

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"

_table_initialized = False


async def log_failed_drug(drug_names: list[str], source: str) -> None:
    """Log failed drug lookup to the database and send a Pushover notification.

    Args:
        drug_names: List of drug names involved in the failed lookup (1–5 drugs).
        source: Identifier for the failing component (e.g. 'rxnorm_pubchem',
            'ddinter_no_interaction', 'openfda_no_reports').

    """
    global _table_initialized
    timestamp = datetime.now(UTC)

    logger.error(
        f"Drug lookup failed - Drugs: {drug_names}, Source: {source}, Time: {timestamp}"
    )

    # Write to database
    if os.getenv("DATABASE_URL"):
        try:
            pool = await get_db_pool()
            try:
                if not _table_initialized:
                    # Safety net: table should already exist (created at startup),
                    # but ensure it for RxNorm failures that occur before DDInter runs.
                    await init_failed_lookups_table(pool)
                    _table_initialized = True  # noqa: PLW0603
                async with pool.acquire() as conn:
                    await conn.execute(
                        "INSERT INTO failed_drug_lookups (drugs, source, failed_at) VALUES ($1, $2, $3)",
                        drug_names,
                        source,
                        timestamp,
                    )
                logger.info(f"Logged failed lookup to DB: {drug_names} ({source})")
            finally:
                await pool.close()
        except Exception as e:
            logger.error(f"Failed to write failed lookup to DB: {e}")

    # Send Pushover notification
    app_token = os.getenv("PUSHOVER_APP_TOKEN")
    user_key = os.getenv("PUSHOVER_USER_KEY")

    if not app_token or not user_key:
        logger.warning("Pushover credentials not set — skipping notification")
        return

    try:
        response = httpx.post(
            PUSHOVER_API_URL,
            data={
                "token": app_token,
                "user": user_key,
                "title": f"DrugX Alert: lookup failed ({source})",
                "message": f"Drugs: {', '.join(drug_names)}\nSource: {source}\nTime: {timestamp.isoformat()}",
            },
        )

        if response.status_code == 200 and response.json().get("status") == 1:
            logger.info(f"Pushover notification sent for: {drug_names}")
        else:
            logger.warning(
                f"Pushover notification failed for {drug_names}: {response.text}"
            )

    except Exception as e:
        logger.error(f"Failed to send Pushover notification for {drug_names}: {e}")
