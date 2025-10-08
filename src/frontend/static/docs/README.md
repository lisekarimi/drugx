# DrugX Documentation

## 🧭 Overview

**DrugX** is an AI-powered clinical decision support tool that prevents dangerous drug combinations by analyzing medication interactions using trusted medical databases and real-world adverse event data.

<img src="https://github.com/lisekarimi/drugx/blob/main/assets/img/fullpage.png?raw=true" alt="DrugX interface" width="450">

## ⚙️ How It Works

DrugX follows a 4-step validation pipeline:

1. **Normalize** drug names via RxNorm (with PubChem fallback)
2. **Check interactions** against DDInter database (PostgreSQL)
3. **Fetch adverse events** from OpenFDA's FAERS system
4. **Summarize findings** with AI into clear risk levels and actionable safety notes

## 🌟 Key Features

- **Medical-grade accuracy** using curated databases (no hallucinated interactions)
- **Real-world safety data** from FDA adverse event reports
- **Modular architecture** supporting easy integration of new data sources
- **Production-ready** with comprehensive unit testing and CI/CD
- **Kubernetes deployment** for GCP, AWS, or local clusters
- **Built with Python 3.11**, Streamlit frontend, and PostgreSQL backend

## 🧰 Technology Stack

- **Backend:** RxNorm • DDInter • OpenFDA • PubChem • LLM Analysis
- **Frontend:** Streamlit
- **Infrastructure:** Docker • Kubernetes • GitHub Actions
- **Database:** PostgreSQL (cloud-hosted with connection pooling)


---

⚠️ **Medical Disclaimer:** DrugX is a clinical decision support tool for informational purposes only—not a substitute for professional medical advice. Always consult healthcare providers for medical decisions.
