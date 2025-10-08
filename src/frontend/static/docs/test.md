# 🧪 Unit Testing Guide

This guide covers the unit testing approach for the DrugX drug interaction analysis system.

## 📋 Overview

The test suite covers 5 main API clients:
- API clients for drug data retrieval and interaction checking
- Comprehensive mocking to avoid external API calls
- Async testing support with pytest-asyncio
- Automated testing via GitHub Actions CI
- Code quality enforcement with Ruff linting

## 🚀 Testing Commands

```bash
# Run all tests
make test
```

All testing commands are available in the Makefile. See `make help` for additional options.

## 🔄 CI/CD Integration

Testing is automated via GitHub Actions:
- **Code Quality**: Ruff linting and formatting checks
- **Unit Tests**: Full test suite runs on feature branches, dev, and main
- **Coverage Reports**: Generated only on main branch pushes
- **Branch Protection**: Tests must pass before merging

## 🛠️ Client Testing Approaches

### 🧬 PubChem Client
**File:** `tests/test_pubchem_client.py`

Tests the PubChem API client for drug synonym retrieval.

**Key test areas:**
- Successful synonym retrieval and cleaning
- API error handling (fault responses, HTTP errors)
- URL encoding for drug names with spaces
- Empty response handling

**Mocking strategy:**
```python
# Mock HTTP responses
with patch.object(client, "_make_request") as mock_request:
    mock_request.return_value = SYNONYMS_RESPONSE
```

### 💊 RxNorm Client
**File:** `tests/test_rxnorm_client.py`

Tests drug normalization using RxNorm database with PubChem fallback.

**Key test areas:**
- Exact and approximate RxCUI matching
- Drug information retrieval (ingredients, classes)
- PubChem synonym fallback
- Error handling for missing drugs

**Mocking strategy:**
```python
# Mock RxNorm API calls
@patch("src.clients.rxnorm.RxNormClient._make_request")
async def test_get_rxcui_exact_match(self, mock_request):
    mock_request.return_value = ASPIRIN_RXCUI_RESPONSE
```

### ⚡ DDInter Client
**File:** `tests/test_ddinter_client.py`

Tests drug interaction checking with PostgreSQL database.

**Key test areas:**
- High-level wrapper function testing
- Direct client method testing (avoiding complex database mocking)
- Interaction summary with category explanations
- Error handling for missing interactions

**Mocking strategy:**
```python
# Method-level mocking to avoid database complexity
with patch.object(client, "check_interaction") as mock_check:
    mock_check.return_value = interaction_data
```

### 📊 OpenFDA Client
**File:** `tests/test_openfda_client.py`

Tests adverse event data retrieval from FAERS database.

**Key test areas:**
- Multi-drug adverse event queries
- Data processing and aggregation
- HTTP error handling (404, timeouts)
- PubChem synonym fallback

**Mocking strategy:**
```python
# Mock HTTP session responses
with patch.object(client.session, "get") as mock_get:
    mock_response.json.return_value = ADVERSE_EVENTS_RESPONSE
```

### 🤖 LLM Client
**File:** `tests/test_llm_client.py`

Tests LLM analysis with OpenAI primary and Claude fallback.

**Key test areas:**
- Provider fallback logic (OpenAI → Claude)
- API key validation
- Prompt creation from input data
- Error handling for both providers

**Mocking strategy:**
```python
# Method-level mocking to avoid API calls
@patch("src.clients.llm.LLMClient._call_openai_gpt4")
async def test_analyze_success_openai(self, mock_openai):
    mock_openai.return_value = "Analysis result"
```

## 🔧 Testing Patterns

### Async Testing
All API clients use async/await patterns:
```python
@pytest.mark.asyncio
async def test_async_method(self):
    result = await client.some_async_method()
    assert result is not None
```

### Context Manager Testing
Clients implement async context managers:
```python
async def test_context_manager(self):
    async with ClientClass() as client:
        result = await client.method()
    # Client properly cleaned up
```

### Error Handling
Each client tests custom exceptions:
```python
async def test_custom_error(self):
    error = CustomError("message")
    assert "message" in str(error)
```

## ⚙️ Configuration

### Test Setup
**File:** `tests/conftest.py`

Required configuration for async testing and shared fixtures:
```python
# Enable pytest-asyncio plugin
pytest_plugins = ("pytest_asyncio",)

@pytest.fixture
def mock_http_session():
    """Mock httpx.AsyncClient for all API clients."""

@pytest.fixture
def sample_drug_data():
    """Common test drug data for all modules."""
```

### pytest.ini or pyproject.toml
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Test Dependencies
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `pytest-cov` - Coverage reporting

## 📈 Coverage Summary

```
Name                           Coverage
------------------------------------------
src/clients/pubchem.py           100%
src/clients/openfda.py            93%
src/clients/rxnorm.py             65%
src/clients/llm.py                59%
src/clients/ddinter.py            47%
------------------------------------------
TOTAL                             69%
```

## 🔧 Maintenance Notes

- **No external API calls**: All tests use mocking to avoid network dependencies
- **Database isolation**: DDInter tests avoid complex database mocking by testing at method level
- **Predictable responses**: Mock data simulates real API responses for reliable testing
- **Error simulation**: Tests cover both success and failure scenarios

## ➕ Adding New Tests

1. Follow existing patterns for your client type
2. Mock at the appropriate level (HTTP session vs method calls)
3. Test both success and error paths
4. Include edge cases (empty responses, malformed data)
5. Verify proper cleanup in async context managers
