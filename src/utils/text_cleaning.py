# src/utils/text_cleaning.py

import re


def clean_drug_name(drug_name: str) -> str:
    """Clean drug name by keeping only letters and spaces.

    Args:
        drug_name: Raw drug name that may contain punctuation/numbers

    Returns:
        Cleaned drug name with only letters and spaces

    """
    if not drug_name:
        return ""

    cleaned = re.sub(r"[^a-zA-Z\s]", "", drug_name).strip()
    return cleaned
