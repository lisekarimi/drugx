---
title: DrugX
emoji: 💊
colorFrom: blue
colorTo: purple
sdk: docker
short_description: AI Platform for Preventing Dangerous Drug Mixes
---

# 💊 DrugX – AI Platform for Preventing Dangerous Drug Mixes

DrugX is an AI tool that checks medicine interactions to prevent dangerous side effects and keep patients safe.

It works by:
- **Standardizing medicine names** (so brand, generic, or even misspelled names are recognized).
- **Checking for known interactions** using trusted medical databases.
- **Looking at real-world safety reports** from the FDA’s adverse event system.
- **Summarizing the results with AI** into clear risk levels and safety notes.

This way, DrugX helps patients and clinicians avoid harmful drug combinations while staying simple to use and medically reliable.

## 🌐 Production Link
[🚀 **Try the Live Demo**](https://huggingface.co/spaces/lisekarimi/drugx)

## 📸 Screenshots
<img src="https://github.com/lisekarimi/drugx/blob/main/assets/img/fullpage.png?raw=true" alt="DrugX interface" width="450">

## ⚙️ Pre-requisites
**Development Tools:**
- Python **3.11.x** (not 3.12+)
- [uv package manager](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Make:
  - Windows: `winget install GnuWin32.Make`
  - macOS: `brew install make`
  - Linux: `sudo apt install make`

## 🏗️ Project Structure
- The **backend** is built around specialized API clients (`rxnorm`, `openfda`, `ddinter`, and `pubchem`) that handle normalization, interaction lookups, and adverse event retrieval.
- The **frontend** is a **Streamlit app** that lets users enter medications, runs the analysis pipeline, and displays results with clear risk levels and safety notes.
- For **data analysis**, a Jupyter notebook (`data/notebooks/data_exploration.ipynb`) was used for EDA of the DDInter dataset, ensuring data quality and consistency before loading it into PostgreSQL.

## 🚀 Installation Instructions

1. **Clone the Repository**:
   ```bash
    git clone https://github.com/lisekarimi/drugx.git
    cd drugx
    ```

2. **Set Up Environment**:

   ```bash
   cp .env.example .env
   # fill in API keys and DB URI
   uv sync
   ```

3. **Environment Variables Required**:

Check `.env.example` — all required environment variables are listed there.

## 📚 Documentation

Detailed documentation for each component (RxNorm, DDInter, OpenFDA, PubChem, LLM, Monitoring, and testing) is available in the
[project Wiki.](https://github.com/lisekarimi/drugx/wiki)

## ▶️ Usage

Start services (app + database + jupyter):

```bash
make up
```

## 🧭 Architecture Overview

DrugX follows a modular, plug-and-play design:
- **Workflow**: Normalize drug names → check interactions (DDInter) → fetch adverse events (OpenFDA) → summarize with AI.
- **Components**: RxNorm, DDInter, OpenFDA, PubChem, LLM, and Monitoring.
- **Extensible**: New data sources or databases can be added easily without changing the core pipeline.

<img src="https://github.com/lisekarimi/drugx/blob/main/assets/img/archi.png?raw=true" alt="DrugX interface" width="450">


👉 [Read the full architecture documentation](https://github.com/lisekarimi/drugx/wiki/Architecture)

## 🧪 Unit Testing

Run tests:

```bash
make test
```
Other test commands are available in the Makefile.

👉 [Read the full testing documentation](https://github.com/lisekarimi/drugx/wiki/Testing_Strategy)

## 🛠️ Development

- **Lint & Fix**: `make lint` | `make fix`
- **Hooks**: `make install-hooks`
- **Secrets**: Gitleaks scans for sensitive data
- **CI/CD**: GitHub Actions runs build, lint, and tests
- **DB**: Use PostgreSQL in a cloud environment (e.g. Supabase, which offers free session pooling for concurrent access).

## 🚀 Deployment

### Production Deployment
- **Hugging Face Spaces**: Deployment triggered manually via GitHub Actions when "deploy" is committed (see `.github/workflows/deploy-hf.yml` for details)

### Kubernetes Deployment
This project includes Kubernetes deployment files for cloud deployment on GCP, AWS, or local clusters:

```bash
# Deploy to Kubernetes cluster
make k8s-build
make k8s-deploy
make k8s-url
```

The same YAML files can be used to deploy on Google Kubernetes Engine (GKE), Amazon EKS, or any Kubernetes cluster.

## 🛡️ Medical Safety Note

* DrugX is a **clinical decision support tool**, not a prescribing authority.
* **No hallucinated mechanisms**: only DDInter + curated rules.
* **Disclaimers included** when no interaction is found.
