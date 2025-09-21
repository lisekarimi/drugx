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
OPENAI_MODEL = "gpt-4o-mini"
CLAUDE_MODEL = "claude-3-5-sonnet-20241022"

# LLM parameters
LLM_MAX_TOKENS = 2000
LLM_TEMPERATURE = 0.1  # Low temperature for consistent, factual responses
LLM_TIMEOUT = 60.0  # Timeout in seconds
ANTHROPIC_VERSION = "2023-06-01"

# API Keys (from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

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
- Simple Summary: Use everyday language, under 50 words total, focus on actions
- Detailed Analysis: Medical terms OK, comprehensive technical information
- Be specific to these exact drugs and their interaction data
- Avoid generic advice like "consult your doctor" - explain WHY they should consult
- Reference actual findings (e.g., "moderate bleeding risk found" not "may interact")
- When analyzing multiple drugs, address ALL pairwise interactions found
- For 3+ drug combinations, assess cumulative risk from multiple interactions
- Don't focus only on the highest severity interaction - explain the overall combination safety
"""
