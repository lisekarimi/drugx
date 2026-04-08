# 💊 OpenFDA API Client

A Python client for retrieving adverse event statistics from the FDA Adverse Event Reporting System (FAERS) database via the OpenFDA API.

## ❓ Why Adverse Event Context?

When evaluating drug combinations, understanding real-world adverse event reports provides valuable context:
- **Safety signals**: Patterns in reported adverse events may indicate potential issues
- **Contextual awareness**: Helps users understand if a combination has been associated with serious outcomes
- **Informed decisions**: Provides additional data points beyond theoretical interaction databases

**Important**: This data is for contextual information only, not authoritative interaction data. FAERS reports are voluntary and unverified - they cannot prove causation.

## 🔄 Input → Processing → Output

### 📥 Input
List of drug ingredient names:
- 2+ drug names required (single drugs return empty result)
- Brand or generic names: ["aspirin", "warfarin"]
- Case-insensitive matching

### ⚙️ Processing
1. Query OpenFDA for reports containing all specified drugs
2. If no results, attempt PubChem synonym fallback
3. Analyze sample of up to 100 reports
4. Extract serious event counts, reaction types, and dates
5. Return aggregate statistics

### 📤 Output JSON

**Success (reports found):**
```json
{
  "adverse_events": {
    "drugs": ["aspirin", "warfarin"],
    "n_reports": 1247,
    "n_serious": 89,
    "top_reactions": [
      "Gastrointestinal haemorrhage",
      "International normalised ratio increased",
      "Haemorrhage",
      "Haematochezia",
      "Melaena"
    ],
    "last_report_date": "2024-12-15",
    "sample_size": 100
  }
}
```

**No reports found:**
```json
{
  "adverse_events": {
    "drugs": ["drug1", "drug2"],
    "n_reports": 0,
    "n_serious": 0,
    "top_reactions": [],
    "last_report_date": null,
    "sample_size": 0,
    "reason": "No reports found after synonym search"
  }
}
```

**Error (graceful degradation):**
```json
{
  "adverse_events": {
    "drugs": ["drug1", "drug2"],
    "n_reports": 0,
    "n_serious": 0,
    "top_reactions": [],
    "last_report_date": null,
    "sample_size": 0,
    "error": "OpenFDA failed: connection timeout"
  }
}
```

## 🚀 Quick Start

```python
from src.clients.openfda import get_adverse_event_context_safe

# Basic usage - never raises exceptions
result = await get_adverse_event_context_safe(["aspirin", "warfarin"])
events = result["adverse_events"]

if events["n_reports"] > 0:
    print(f"Found {events['n_reports']} FAERS reports")
    print(f"Sample analyzed: {events['sample_size']} reports")
    print(f"Serious events in sample: {events['n_serious']}")
```

## ⚠️ Error Handling

**Exception Types:**
- `OpenFDAError`: API errors with optional status code

**Safe Wrapper:**
- `get_adverse_event_context_safe()`: Never raises exceptions, returns error in JSON

**Automatic Fallbacks:**
1. 404 response → Try PubChem synonyms
2. Network errors → Retry up to 3 times with exponential backoff
3. All retries fail → Return empty result with error message

## 🔧 Configuration

Default settings in `src/clients/openfda.py`:
- 30 second timeout
- 3 retries with exponential backoff (2-8 seconds)
- Sample size: 100 reports per query
- Automatic PubChem synonym fallback

## 🌐 API Usage & Limits

### 🏛️ OpenFDA API
- **Provider**: U.S. Food and Drug Administration
- **Cost**: Free
- **Rate Limits**: 240 requests per minute, 120,000 per day (without API key)
- **Registration**: Optional (API key increases limits to 240/min, unlimited daily)
- **Base URL**: `https://api.fda.gov/drug/event.json`

### 🧪 PubChem Fallback
- **When**: Automatic fallback when OpenFDA returns no results
- **Process**: Retrieves synonyms for each drug, tests combinations
- **Purpose**: Catches brand names, alternative spellings, and chemical variations

### 🔗 Endpoint Used
- `/drug/event.json` - Search adverse event reports

**Query Structure:**
```
patient.drug.medicinalproduct:"drug1"+AND+patient.drug.medicinalproduct:"drug2"
```

### 📊 Data Sampling
- **Total reports**: Retrieved from API metadata (authoritative count)
- **Serious events**: Counted from sample only (representative, not exhaustive)
- **Reactions**: Extracted from sample (top 5 most common MedDRA terms)
- **Transparency**: `sample_size` field shows how many reports were analyzed

### 📜 Fair Usage
The client implements responsible API usage:
- Proper User-Agent identification
- Reasonable timeouts to avoid hanging requests
- Retry logic with exponential backoff
- Logging of failed queries

**Note**: For high-volume usage, consider registering for an API key at [open.fda.gov](https://open.fda.gov/apis/authentication/).

## 📋 Understanding FAERS Data

**What FAERS Contains:**
- Voluntary adverse event reports from healthcare professionals, consumers, and manufacturers
- Reports submitted to FDA since 2004
- Both serious and non-serious events

**Important Limitations:**
- Reports are unverified and may be incomplete
- Cannot establish causation (drugs may be coincidentally associated)
- Reporting biases (newer drugs, serious events more likely to be reported)
- Duplicate reports possible
- Not all adverse events are reported

**Use Cases:**
- Contextual safety information during drug interaction checks
- Signal detection for further investigation
- Understanding real-world reporting patterns

**NOT for:**
- Proving drug interactions cause specific adverse events
- Comparing safety between drugs (reporting rates vary)
- Clinical decision-making as sole source of evidence
