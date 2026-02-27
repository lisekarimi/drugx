## [0.2.0]

### ✨ Added
- Documentation support using Docsify accessible at `/docs/` endpoint
- ChatBot widget integration for enhanced user interaction
- Pushover push notifications for failed drug lookups (replaces Resend email)
- `failed_drug_lookups` PostgreSQL table to track all failed lookups with source and timestamp
- RxNorm spelling suggestions fallback for drug name typos (e.g. "Paracitamol" → "paracetamol")
- RxNorm approximate search candidate retry for improved drug name resolution
- `make db-load` command to bulk-load DDInter data into cloud PostgreSQL

### 🔧 Changed
- Monitoring replaced: n8n + email workflow removed in favor of Pushover + DB tracking
- `log_failed_drug` now async, accepts `list[str]`, writes to DB and sends Pushover notification
- `get_db_pool()` strips `sslmode` from URL for asyncpg compatibility with Supabase
- Docker build uses `pip install uv` instead of pulling from `ghcr.io/astral-sh/uv`

### 🗑️ Removed
- Resend email dependency and configuration
- Local PostgreSQL service from Docker Compose
- n8n workflow references from documentation

## [0.1.0]

### ✨ Added
- Streamlit frontend for drug interaction checks.
- LLM analysis (GPT-4 with Claude fallback).
- RxNorm, DDInter, OpenFDA, and PubChem clients.
- PostgreSQL DDInter database integration.
- n8n workflow for failed lookup monitoring via Telegram.
- Unit tests for all clients + CI/CD with GitHub Actions.
- Docker + Docker Compose setup for local development.
- Jupyter notebook for DDInter data exploration.
- Gitleaks for secret scanning and security checks.
- Documentation for each system component.
