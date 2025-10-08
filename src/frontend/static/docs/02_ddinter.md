
# 💊 DDInter Database Client

A PostgreSQL-based client for checking drug interactions using the DDInter database.

## 🔄 Pipeline Overview

1. **📥 Data Acquisition**

    * Webscraper downloads 8 DDInter CSVs (`A,B,D,H,L,P,R,V`) from https://ddinter.scbdd.com/download/
    * Consolidates them into `ddinter_all.csv` with category tags

2. **📊 Data Analysis (EDA)**

    Performed in `data/notebooks/data_exploration.ipynb` to understand the dataset before using it.

   * No missing values
   * No flipped duplicates (A–B vs B–A)
   * Same drug pairs repeated across categories with consistent severity
   * Valid multi-category annotations preserved

3. **⚙️ Data Processing**

    * Processor aggregates duplicate pairs → merges categories into `"A,D,H"`
    * Creates **final dataset** `ddinter_pg.csv` → 160,235 unique interactions

4. **🗄️ Database Storage**

    Drug interaction checking requires fast, reliable access to comprehensive interaction data.
    CSV file scanning becomes impractical with 160,000+ interaction records, while PostgreSQL provides:

    - **Instant lookups**: Indexed bidirectional searches (A+B or B+A) in milliseconds
    - **Production reliability**: Connection pooling, transactions, and concurrent access
    - **Scalability**: Handles large datasets efficiently without memory constraints
    - **Data integrity**: Constraints and validation ensure data consistency

    This client bridges the gap between raw DDInter research data and production-ready drug interaction checking for healthcare applications.

5. **🔑 Client Access**

   * Async **DDInterClient** connects to PostgreSQL
   * Handles auto-setup if DB is empty
   * Provides structured JSON outputs for LLM synthesis

## 🗂️ Database Schema
```sql
CREATE TABLE ddinter (
    ddinter_id_a TEXT NOT NULL,
    ddinter_id_b TEXT NOT NULL,
    drug_a VARCHAR(255) NOT NULL,
    drug_b VARCHAR(255) NOT NULL,
    severity severity_level NOT NULL,  -- Minor|Moderate|Major|Unknown
    categories TEXT NOT NULL,          -- "A,B,D" comma-separated
    UNIQUE(ddinter_id_a, ddinter_id_b)
);
```

## 🔍 Input → Processing → Output

### ⬅️ Input

Normalized ingredient names from RxNorm client:

* Standard names: "aspirin", "warfarin", "acetaminophen"
* Case-insensitive matching
* Multiple drugs supported for pairwise checking

### ⚙️ Processing

1.Bidirectional PostgreSQL query with case-insensitive matching

2.PubChem synonym fallback when direct matching fails

3.Category parsing from comma-separated strings

4.Medical disclaimer generation for non-interactions

5.Email notifications for failed interaction lookups

6.Automatic database setup if empty

### 📤 Output JSON

#### ✅ Interaction Found

```json
{
  "severity": "Moderate",
  "drugs": ["Acetaminophen", "Warfarin"],
  "category_explanations": {
    "B": "Blood and blood-forming organs"
  }
}
```

#### ⚠️ No Interaction Found

```json
{
  "drugs": ["aspirin", "acetaminophen"],
  "severity": null,
  "note": "The DDInter database doesn't list any known, clinically significant pharmacokinetic or pharmacodynamic interaction between these drugs. This does not mean the combination is guaranteed 100% safe—it means that based on available published interaction data, no meaningful interaction has been established."
}
```

#### 🔄 Multi-Drug Check

```json
[
  {"drugs": ["aspirin", "warfarin"], "severity": "Major", ...},
  {"drugs": ["aspirin", "metformin"], "severity": null, ...},
  {"drugs": ["warfarin", "metformin"], "severity": "Minor", ...}
]
```

## 🧪 PubChem REST API (Fallback)
- **When**: Automatic fallback when direct drug name matching fails in DDInter database
- **Process**: Retrieves up to 3 synonyms for both drugs, tests all combinations
- **Purpose**: Finds interactions using alternative drug names when standardized names don't match database entries

For more details about PubChem integration, refer to the PubChem section.


## ⚡ Quick Start

```python
from src.clients.ddinter import check_drug_interactions_consolidated

# Check multiple drug interactions
ingredients = ["aspirin", "warfarin", "acetaminophen"]
interactions = await check_drug_interactions_consolidated(ingredients)

for interaction in interactions:
    drugs = interaction['drugs']
    severity = interaction.get('severity', 'None')
    print(f"{drugs[0]} + {drugs[1]}: {severity}")
```

## 📐 Architecture Highlights

* **Auto-setup**: Detects empty DB, loads CSV once
* **Async client**: Connection pooling + error handling
* **LLM-ready**: Outputs structured JSON for synthesis

## 🗄️ Database Performance

* **Size**: 160,235 unique interactions
* **Lookup speed**: <10ms with indexes
* **Concurrent access**: 100+ users supported
* **Memory use**: Efficient, no full dataset loading
* **Indexes**: `(lower(drug_a), lower(drug_b))` for bidirectional lookups, `(ddinter_id_a, ddinter_id_b)` for unique pair enforcement

## 🛡️ Medical Safety Note

* **No mechanism fabrication**: Only DDInter + curated rules
* **Disclaimers included** when no interaction is found
* Designed for **clinical decision support**, not absolute safety guarantees


## 🏗️ Database Deployment Options

### 🚀 Production: Cloud PostgreSQL (Recommended)

For production deployments, managed PostgreSQL services provide better reliability, scalability, and maintenance.

**Current setup uses Supabase :**
Choose Session pooler
update .env with the appopraite URI
```bash
POSTGRESQL_ADDON_URI=
```

Here’s a tightened-up version of your section with smoother grammar and phrasing:


### 🛠️ Local Development: Docker PostgreSQL (Optional)

For offline development or isolated testing:

**1. Uncomment the PostgreSQL service in `docker-compose.yml`.**

**2. Update the app service to depend on Postgres:**

```yaml
app:
  environment:
    - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
  depends_on:
    postgres:
      condition: service_healthy
```

**3. Add local credentials to `.env`:**

```bash
POSTGRES_DB=medguard
POSTGRES_USER=medguard
POSTGRES_PASSWORD=your_local_password
```

**4. Start the app with the local database:**

```bash
make up  # Starts both the app and Postgres services
```

**Architecture benefits**: Using a managed cloud PostgreSQL instance gives production-grade performance, automated backups, and removes Docker maintenance overhead, while keeping the same application code thanks to environment-based configuration.
