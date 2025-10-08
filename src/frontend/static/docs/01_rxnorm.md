# 💊 RxNorm API Client

A Python client for normalizing drug names using the RxNorm REST API.

## ❓ Why Drug Name Normalization?

Drug interaction checking requires standardized drug names, but users enter drugs in many different ways:
- Brand names vs generic names ("Tylenol" vs "acetaminophen")
- Different salt forms ("warfarin" vs "warfarin sodium")
- Spelling variations and typos
- Partial or incomplete names

Without normalization, a drug interaction system would miss dangerous interactions because it can't recognize that "Coumadin" and "warfarin sodium" are the same medication. This client solves that by converting all drug name variations into standardized identifiers and ingredient names that downstream systems can reliably use for interaction checking.

## 🔄 Input → Processing → Output

### 📥 Input
Any drug name string:
- Brand names: "Tylenol", "Coumadin"
- Generic names: "acetaminophen", "warfarin"
- Salt forms: "warfarin sodium", "aspirin hydrochloride"
- Typos: "aspirine", "warafin"
- Partial names: "aspir"

### ⚙️ Processing
1. Exact search in RxNorm database
2. Fuzzy matching if no exact match
3. PubChem synonym fallback if RxNorm search fails
4. Salt suffix removal and cleaning
5. Drug classification lookup

### 📤 Output JSON

**Success:**
```json
{
  "rxcui": "1191",
  "in": "aspirin",
  "classes": {
    "epc": ["Nonsteroidal Anti-inflammatory Drug", "Platelet Aggregation Inhibitor"],
    "moa": ["Cyclooxygenase Inhibitors"],
    "pe": ["Decreased Platelet Aggregation", "Decreased Prostaglandin Production"],
    "atc": ["B01AC06", "N02BA01"]
  }
}
```

**Suggestions (when drug not found but similar ones exist):**
```json
{
  "candidates": ["aspirin", "asparagine", "asparaginase"]
}
```

**Error (when no matches found):**
```json
{
  "error": "Drug 'invalidname123' not found"
}
```

## 🚀 Quick Start

```python
from src.clients.rxnorm import normalize_drug_safe

# Basic usage
result = await normalize_drug_safe("aspirin")
if "error" not in result:
    print(f"Drug: {result['in']}, RxCUI: {result['rxcui']}")
```

## ⚠️ Error Handling

Two exception types:
- `DrugNotFoundError`: Drug not in database (may include candidates)
- `RxNormAPIError`: API connectivity issues

## 🔧 Configuration

Default settings in `src/clients/rxnorm.py`:
- 30 second timeout
- 3 retries with exponential backoff
- Automatic salt suffix removal

## 🌐 API Usage & Limits

### 🏥 RxNorm REST API
- **Provider**: National Library of Medicine (NLM)
- **Cost**: Free
- **Rate Limits**: None officially documented
- **Registration**: Not required
- **Base URL**: `https://rxnav.nlm.nih.gov/REST/`

### 🧪 PubChem REST API (Fallback)
- **When**: Automatic fallback when RxNorm search fails
- **Process**: Retrieves up to 3 synonyms, tests each in RxNorm
- **Purpose**: Catches alternative names and chemical variations RxNorm misses

For more details about PubChem integration, refer to the PubChem section.

### 🔗 Endpoints Used
- `/rxcui.json` - Exact drug name lookup
- `/approximateTerm.json` - Fuzzy matching for typos
- `/rxcui/{id}/related.json` - Get ingredient names
- `/rxclass/class/byRxcui.json` - Drug classifications

### 📜 Fair Usage
While free and unlimited, the client includes:
- 30-second timeouts to avoid hanging requests
- Exponential backoff retry (3 attempts max)
- Proper User-Agent identification

**Note**: Always verify current NLM terms of service for any usage restrictions.
