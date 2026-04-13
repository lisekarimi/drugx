# src/constants.py
"""Module containing constant values used throughout the application."""

import os
import tomllib
from pathlib import Path

# ==================== PROJECT METADATA ====================
root = Path(__file__).resolve().parent.parent
with open(root / "pyproject.toml", "rb") as f:
    pyproject = tomllib.load(f)

PROJECT_NAME = pyproject["project"]["name"]
VERSION = pyproject["project"]["version"]

# # ==================== API CONFIGURATION ====================
RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_BASE_URL = "https://api.fda.gov"


# # ========================= MAPPING =========================
# ATC Category mappings for DDInter
ATC_CATEGORIES = {
    "A": "Alimentary tract and metabolism",
    "B": "Blood and blood-forming organs",
    "D": "Dermatologicals",
    "H": "Systemic hormonal preparations (excluding sex hormones and insulins)",
    "L": "Antineoplastic and immunomodulating agents",
    "P": "Antiparasitic products, insecticides and repellents",
    "R": "Respiratory system",
    "V": "Various",
}

# ==================== LLM CONFIGURATION ====================
# Model names
CEREBRAS_MODEL = "gpt-oss-120b"
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

# LLM parameters
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 0.1  # Low temperature for consistent, factual responses
LLM_TIMEOUT = 60.0  # Timeout in seconds

# API Keys (from environment)
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")

# ==================== LLM PROMPTS ====================
LLM_SYSTEM_PROMPT = "You are a clinical pharmacology expert specializing in drug interaction analysis and medication safety. Provide evidence-based, cautious analysis while always emphasizing the need for professional medical consultation."

LLM_USER_PROMPT_TEMPLATE = """Analyze these drug interaction data sources and provide both a simple summary and detailed analysis.

**DATA SOURCES:**
1. **RxNorm:** {rxnorm_json}
2. **DDInter:** {ddinter_json}
3. **OpenFDA:** {openfda_json}

**OUTPUT FORMAT:**

## 🚨 BOTTOM LINE
- **Risk Level**: [SAFE/LOW RISK/MODERATE RISK/HIGH RISK/AVOID]
- **What it means**: [Plain language - no medical terms]
- **What to do**: [Specific advice based on actual data found]
- **Important**: [Customized warning for this combination]

## 📋 DETAILED ANALYSIS
1. **Drug Summary** 2. **Interaction Analysis** 3. **Real-World Data** 4. **Clinical Recommendations** 5. **Limitations**

**KEY RULES:**
- Stick strictly to the provided data — no outside knowledge or assumptions
- If a source has no results, say so; never fill gaps from general knowledge
- Bottom Line: plain language, under 50 words, action-focused
- Detailed Analysis: cite actual findings, not generic statements
- Cover ALL pairwise interactions and overall combination risk
"""
