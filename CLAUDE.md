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
```

### Environment Setup
```bash
cp .env.example .env   # Fill in DATABASE_URL, OPENAI_API_KEY, ANTHROPIC_API_KEY
uv sync
```

## Architecture

### Analysis Pipeline (sequential, all async)
`src/frontend/app.py` → `analyze_medications()` runs these four steps:

1. **RxNorm normalization** (`src/clients/rxnorm.py`): Converts brand/misspelled names to standardized ingredient names. Falls back to PubChem synonyms if RxNorm fails.
2. **DDInter interaction check** (`src/clients/ddinter.py`): Queries a PostgreSQL table loaded from the DDInter dataset. Falls back to PubChem synonyms for fuzzy matching.
3. **OpenFDA adverse events** (`src/clients/openfda.py`): Fetches real-world FAERS reports for the drug combination. Falls back to PubChem synonyms.
4. **LLM analysis** (`src/clients/llm.py`): Synthesizes all data into a structured risk assessment. Uses OpenAI GPT-4o-mini as primary, Claude 3.5 Haiku as fallback.

### PubChem as Cross-Cutting Fallback
`src/clients/pubchem.py` provides synonym lookup used by RxNorm, DDInter, and OpenFDA clients when their primary lookups fail. This is the main resilience mechanism across the pipeline.

### Database
- PostgreSQL via `asyncpg` connection pool (`src/utils/database.py`)
- Single table: `ddinter` with columns `drug_a`, `drug_b`, `severity` (enum: Minor/Moderate/Major/Unknown), `categories`
- Cloud-hosted (e.g., Supabase) in production; `DATABASE_URL` env var required
- Table auto-initializes with CSV data on first run if empty (`setup_database()`)
- Row Level Security (RLS) enabled with public read access

### Frontend
- Streamlit app (`src/frontend/app.py`) with session state for analysis results
- Accepts 2–5 medications, runs the pipeline, and renders risk level with CSS classes
- CSS in `src/frontend/styles.css`, static docs served from `src/frontend/static/`

### Constants & Configuration
`src/constants.py` is the single source for all configuration:
- API base URLs, LLM model names, LLM prompts, API keys from environment
- Project name/version read from `pyproject.toml` via `tomllib`

### Error Handling Pattern
Each client defines custom exceptions (`DrugNotFoundError`, `InteractionNotFoundError`, `OpenFDAError`, etc.) and exposes `_safe` wrapper functions that never raise—they log failures and return graceful defaults. Failed drug lookups are logged via `src/utils/log_failed_drug.py`.

### Ruff Configuration
Docstrings (`D` rules) are enforced. Notebooks are excluded. `E501` (line length) is ignored.

### Test Structure
Tests in `tests/` use `AsyncMock` for HTTP session mocking. `asyncio_mode = "auto"` is set in `pyproject.toml` so all async tests run without explicit `@pytest.mark.asyncio`.

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
| `src/utils/database.py` | asyncpg pool, DDInter table init, CSV bulk load |
| `data/ddinter_pg.csv` | Processed interaction data loaded into PostgreSQL |
