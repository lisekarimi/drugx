# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DrugX is an AI platform that checks drug-drug interactions. It normalizes medication names, queries interaction databases, fetches real-world adverse event data, and summarizes findings using LLMs.

**Python version**: 3.11.x strictly (not 3.12+). Package manager: `uv`.

## Commands

### Development
```bash
make up            # Start all services (app + Jupyter) via Docker Compose
make app           # Start app service only (uses cloud PostgreSQL)
make down          # Stop all services
```

### Testing
```bash
make test                          # Run all tests
make test-cov                      # Run tests with coverage
# Run a single test file:
uv run --isolated --with pytest --with pytest-asyncio pytest tests/test_rxnorm_client.py
# Run a single test function:
uv run --isolated --with pytest --with pytest-asyncio pytest -k test_function_name
```

### Linting
```bash
make lint   # Check with ruff (no fixes)
make fix    # Auto-fix and format with ruff
```

### Data Pipeline
```bash
make data-download   # Scrape DDInter CSV files
make data-process    # Process CSVs into ddinter_pg.csv (loaded into PostgreSQL)
make db-load         # Bulk-load ddinter_pg.csv into cloud PostgreSQL
```

### Environment Setup
```bash
cp .env.example .env   # Fill in DATABASE_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY, PUSHOVER_APP_TOKEN, PUSHOVER_USER_KEY
uv sync                # Requires Python 3.11.x — not compatible with 3.12+
```

### Running Locally
```bash
# Option A — Docker (recommended, matches production):
make app               # Builds image and starts app container

# Option B — without Docker (requires .env and uv sync):
uv run streamlit run src/frontend/app.py
```
Both options require a valid `DATABASE_URL` pointing to the cloud PostgreSQL instance. The `ddinter` table must be populated first — run `make db-load` once if it's a fresh database.

## Architecture

### Analysis Pipeline (sequential, all async)
`src/frontend/app.py` → `analyze_medications()` runs these four steps:

1. **RxNorm normalization** (`src/clients/rxnorm.py`): Converts brand/misspelled names to standardized ingredient names. Fallback chain: approximate search → candidate name retry → RxNorm spelling suggestions → PubChem synonyms.
2. **DDInter interaction check** (`src/clients/ddinter.py`): Queries a PostgreSQL table loaded from the DDInter dataset. Falls back to PubChem synonyms for fuzzy matching.
3. **OpenFDA adverse events** (`src/clients/openfda.py`): Fetches real-world FAERS reports for the drug combination. Falls back to PubChem synonyms.
4. **LLM analysis** (`src/clients/llm.py`): Synthesizes all data into a structured risk assessment. Primary and fallback model names are defined in `src/constants.py`.

### PubChem as Cross-Cutting Fallback
`src/clients/pubchem.py` provides synonym lookup used by RxNorm, DDInter, and OpenFDA clients when their primary lookups fail. This is the main resilience mechanism across the pipeline.

### Database
- PostgreSQL via `asyncpg` connection pool (`src/utils/database.py`)
- `ddinter` table: `drug_a`, `drug_b`, `severity` (enum: Minor/Moderate/Major/Unknown), `categories`; RLS enabled with public read access
- `failed_drug_lookups` table: `drugs TEXT[]`, `source VARCHAR(50)`, `failed_at TIMESTAMPTZ`; indexed on `source` and `failed_at`
- Cloud-hosted only (e.g., Supabase); `DATABASE_URL` env var required. `get_db_pool()` strips `sslmode` from URL and passes `ssl='require'` directly (asyncpg compatibility).
- `ddinter` table auto-initializes with CSV data on first run if empty (`setup_database()`)

### Frontend
- Streamlit app (`src/frontend/app.py`) with session state for analysis results
- Accepts 2–5 medications, runs the pipeline, and renders risk level with CSS classes
- CSS in `src/frontend/styles.css`, static docs served from `src/frontend/static/`

### Constants & Configuration
`src/constants.py` is the single source for all configuration:
- API base URLs, LLM model names, LLM prompts, API keys from environment
- Project name/version read from `pyproject.toml` via `tomllib`

### Error Handling Pattern
Each client defines custom exceptions (`DrugNotFoundError`, `InteractionNotFoundError`, `OpenFDAError`, etc.) and exposes `_safe` wrapper functions that never raise—they log failures and return graceful defaults. `src/utils/log_failed_drug.py` (`log_failed_drug(drug_names: list[str], source: str)`) writes to `failed_drug_lookups` DB table and sends a Pushover push notification (requires `PUSHOVER_APP_TOKEN` + `PUSHOVER_USER_KEY`). Read env vars inside the function, not at module level.

### Ruff Configuration
Docstrings (`D` rules) are enforced. Notebooks are excluded. `E501` (line length) is ignored.

### Test Structure
Tests in `tests/` use `AsyncMock` for HTTP session mocking. `asyncio_mode = "auto"` is set in `pyproject.toml` so all async tests run without explicit `@pytest.mark.asyncio`. **No live database or API keys are needed** — all external calls are mocked. Shared fixtures (mock HTTP session, etc.) live in `tests/conftest.py`.

## Key Files

| Path | Purpose |
|------|---------|
| `src/constants.py` | All config, API keys, LLM prompts |
| `src/frontend/app.py` | Streamlit UI and pipeline orchestration |
| `src/clients/rxnorm.py` | Drug normalization (RxNorm API + PubChem fallback) |
| `src/clients/ddinter.py` | Interaction lookup (PostgreSQL DDInter table) |
| `src/clients/openfda.py` | Adverse event data (OpenFDA FAERS API) |
| `src/clients/llm.py` | LLM synthesis (OpenAI primary, Claude fallback) |
| `src/clients/pubchem.py` | Synonym fallback used by all other clients |
| `src/utils/database.py` | asyncpg pool, DDInter + failed_drug_lookups table init, CSV bulk load |
| `src/utils/log_failed_drug.py` | Async failed-lookup logger: DB write + Pushover notification |
| `data/ddinter_pg.csv` | Processed interaction data loaded into PostgreSQL |
