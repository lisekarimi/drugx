# 🤖 LLM Client for Drug Interaction Analysis

A Python client for synthesizing drug interaction data using OpenAI GPT-4 with Claude Sonnet fallback.

## 🎯 Purpose

Combines structured interaction data from multiple sources (RxNorm, DDInter, OpenFDA) into intelligent clinical analysis and actionable recommendations.

## 🔄 Input → Processing → Output

### 📥 Input
Three JSON datasets from the drug interaction pipeline:
- **RxNorm**: Normalized drug names and classifications
- **DDInter**: Interaction findings with severity levels
- **OpenFDA**: Adverse event statistics from FAERS

### ⚙️ Processing
1. Template-based prompt construction
2. Primary analysis via OpenAI GPT-4
3. Automatic fallback to Claude Sonnet if OpenAI fails
4. Retry logic with exponential backoff

### 📤 Output
Returns structured response with analysis text, provider used, and status indicator.

## 🚀 Quick Start
Use `analyze_drug_interactions_safe()` function with the three data sources as parameters.

## ⚙️ Configuration

```bash
# Required Environment Variables
OPENAI_API_KEY=sk-xxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx
```

**Default Settings:**
All configuration values are defined in `src/constants.py` file.

## 🌐 API Providers

- **Primary**: OpenAI GPT-4 (~$0.01-0.03 per analysis)
- **Fallback**: Anthropic Claude Sonnet (~$0.003-0.015 per analysis)

### 🩺 Why Frontier Models vs Medical LLMs?

Medical LLMs (Meditron, Clinical Camel, etc.) are research models that lack the safety guardrails, clinical validation, and liability coverage that production-grade models provide.

For drug interaction applications:
- **Medical LLMs**: Good for research/benchmarking, but risky (hallucinations, no FDA/EMA reliability)
- **GPT-4/Claude**: Safer, more stable, better at refusing unsafe outputs, already used in health contexts

This is why we use GPT-4/Claude for production medical applications.

## ⚠️ Medical Safety Note

This generates AI-assisted analysis for clinical decision support only. All outputs require professional medical review and cannot replace clinical judgment or current prescribing guidelines.
