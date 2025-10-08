# 🧭 DrugX Architecture

This document provides a detailed overview of the **DrugX architecture**, covering workflow, components, and extensibility.


## 🗺️ Architecture Schema

The following schema shows how DrugX processes inputs through its pipeline

<img src="https://github.com/lisekarimi/drugx/blob/main/assets/img/archi.png?raw=true" alt="DrugX interface">

## 🔌 Plug-and-Play Design

DrugX follows a **modular plug-and-play architecture**:
- Each external data source is wrapped in its own **client module**.
- New databases or APIs can be added by creating a new client without changing the core pipeline.
- This makes DrugX **extensible** (easy to add DrugBank, EMA, WHO databases, etc.) and **maintainable**.


## 📊 Workflow

1. **User Input → Orchestrator**

   Patient/clinician submits a list of medications or supplements in free text.

2. **Normalization (RxNorm + PubChem fallback)**

   Drug names are standardized to RxCUIs and ingredient names. PubChem provides synonyms if RxNorm fails.

3. **Sequential Data Fetch**

   - **DDInter (PostgreSQL)** → curated interaction pairs with severity and categories.
   - **OpenFDA (FAERS)** → adverse event reports for real-world context.

   Both can fall back to PubChem synonyms if needed.

4. **LLM Input**
   The three JSON datasets (RxNorm, DDInter, OpenFDA) are passed unchanged into a templated LLM prompt.

5. **Final Output**

   The LLM generates a **readable summary report** with risk levels, warnings, and disclaimers.

   ⚠️ **Important:** The LLM never judges or overrides severity levels — it only summarizes existing data.

6. **Ops & Monitoring (n8n)**

   A scheduled workflow reads alert emails, aggregates failed lookups, and sends **Telegram summaries** for proactive monitoring.

## 🧩 System Components

### 🔹 RxNorm Client
- Normalizes drug names into **RxCUIs** and ingredients.
- Handles brand names, typos, and salt forms.
- Falls back to PubChem synonyms when RxNorm has gaps.

### 🔹 DDInter Client
- Provides **160k+ curated drug interactions** from PostgreSQL.
- Returns structured results with **severity levels** and **categories**.

### 🔹 OpenFDA Client
- Pulls **adverse event reports** from FAERS.
- Adds real-world safety signals to complement DDInter data.

### 🔹 PubChem Client
- Supplies **synonyms and alternative names** when drugs are missing in other databases.
- Acts as a **universal safety net**.

### 🔹 LLM Client
- Wraps GPT-4 (with Claude fallback).
- Summarizes JSON data into **human-readable risk reports**.
- Includes **disclaimers** and avoids hallucinating new mechanisms.

### 🔹 Monitoring (n8n Workflow)
- Runs every 3 days.
- Aggregates **failed lookups** from email alerts.
- Sends summaries to **Telegram** for team visibility.

## 🏗️ Extensibility

Because each client is modular:
- Adding **DrugBank**, **EMA datasets**, or other APIs requires minimal changes.
- Monitoring can be extended to **Slack, Teams, or email** easily.
- The pipeline remains consistent regardless of which sources are added.


## ☸️ Local Kubernetes Deployment

For local development and testing, the application can be deployed to a Kubernetes cluster using minikube. The project includes Kubernetes manifests (`k8s-deployment.yaml` and `k8s-service.yaml`) that define the deployment and service configurations.

The same YAML configurations can be used for cloud deployments on GKE (Google Kubernetes Engine), EKS (Amazon), or AKS (Azure).
