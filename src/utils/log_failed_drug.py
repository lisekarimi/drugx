# src/utils/log_failed_drug.py
"""Log failed drug lookup notifications."""

import os
from datetime import datetime

import resend

from .logging import logger

# Email configuration
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL")
MONITORING_EMAIL = os.getenv("MONITORING_EMAIL")


def log_failed_drug(drug_name: str, source: str):
    """Log failed drug lookup and attempt email notification."""
    timestamp = datetime.now().isoformat()

    # Always log the failure
    logger.error(
        f"Drug lookup failed - Drug: {drug_name}, Source: {source}, Time: {timestamp}"
    )

    # Attempt to send email notification
    try:
        resend.api_key = os.getenv("RESEND_API_KEY")

        response = resend.Emails.send(
            {
                "from": RESEND_FROM_EMAIL,
                "to": MONITORING_EMAIL,
                "subject": f"DrugX Alert: {drug_name} lookup failed",
                "html": f"<p>Drug lookup failed:</p><ul><li><strong>Drug:</strong> {drug_name}</li><li><strong>Source:</strong> {source}</li><li><strong>Time:</strong> {timestamp}</li></ul>",
            }
        )

        # Check if email was sent successfully
        if response and response.get("id"):
            logger.info(
                f"Email notification sent successfully for failed drug lookup: {drug_name}"
            )
        else:
            logger.warning(f"Email notification failed to send for drug: {drug_name}")

    except Exception as e:
        logger.error(
            f"Failed to send email notification for drug {drug_name}: {str(e)}"
        )
