# 🧪 PubChem API Client

A Python client for retrieving drug synonyms from the PubChem database as a universal fallback mechanism across the drug interaction pipeline.

## 🎯 Purpose

When primary drug searches fail in RxNorm, OpenFDA, or DDInter databases, PubChem provides alternative names and synonyms to expand search coverage. This fallback mechanism increases the likelihood of finding drug matches across all system components.

## 🔄 How It Works

### 📥 Input
Any drug name that failed primary database searches (examples):
- Chemical names: "acetylsalicylic acid"
- Alternative spellings: "paracetamol"
- Trade names: "Advil"

### ⚙️ Processing
1. Search PubChem compound database by name
2. Extract up to 3 synonyms from the compound record
3. Clean and filter synonyms (letters and spaces only)
4. Return cleaned synonym list for retry in original system

### 📤 Output
```python
# Example for "acetylsalicylic acid"
["aspirin", "2-acetoxybenzoic acid", "acetylsalicylate"]
```

## 🔄 Integration Points

- **RxNorm**: When drug normalization fails
- **OpenFDA**: When adverse event searches return no results
- **DDInter**: When interaction database has no matches

## 🚀 Usage

```python
from src.clients.pubchem import get_synonyms

# Get synonyms for a drug name
synonyms = await get_synonyms("acetylsalicylic acid")
# Returns: ["aspirin", "2-acetoxybenzoic acid", "acetylsalicylate"]
```

## 🌐 API Details

### 🏥 PubChem REST API
- **Provider**: National Center for Biotechnology Information (NCBI)
- **Cost**: Free
- **Rate Limits**: No official limits (fair use policy)
- **Base URL**: `https://pubchem.ncbi.nlm.nih.gov/rest/pug`

### 🔗 Endpoint Used
- `/compound/name/{drug_name}/synonyms/JSON` - Get compound synonyms

### ⚙️ Configuration
- 30 second timeout
- 3 retries with exponential backoff (2s, 4s, 8s)
- Returns maximum 3 cleaned synonyms

## ⚠️ Error Handling

- **PubChemAPIError**: API connectivity issues
- **Compound not found**: Returns empty list
- **Invalid responses**: Graceful fallback with logging
