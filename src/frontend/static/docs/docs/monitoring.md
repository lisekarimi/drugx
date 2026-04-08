# 💊 DrugX Failed Lookups Monitoring

DrugX monitors drug lookup failures across all APIs (RxNorm, PubChem, DDInter, OpenFDA) using two complementary mechanisms:

- **Pushover**: Real-time push notification on every failure.
- **`failed_drug_lookups` table**: Persistent DB record for querying patterns over time.

## 🗄️ Database Schema

```sql
CREATE TABLE failed_drug_lookups (
    id        SERIAL PRIMARY KEY,
    drugs     TEXT[]      NOT NULL,   -- e.g. ["aspirin", "warfarin"]
    source    VARCHAR(50) NOT NULL,   -- e.g. "ddinter_no_interaction"
    failed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Source values

| Source | Meaning |
|--------|---------|
| `rxnorm_pubchem` | Drug not found in RxNorm or PubChem |
| `normalization_failed` | Drug found in RxNorm but couldn't be normalized |
| `ddinter_pubchem` | No interaction found even with PubChem synonyms |
| `ddinter_no_interaction` | No interaction entry in DDInter database |
| `openfda_no_reports` | No FAERS reports found even with PubChem synonyms |
| `openfda_error` | OpenFDA API error |

## 🔧 Setup

Add to `.env`:
```
PUSHOVER_APP_TOKEN=your_app_token
PUSHOVER_USER_KEY=your_user_key
```

Get these from your [Pushover dashboard](https://pushover.net):
- **App token**: create an application under your account
- **User key**: shown on the main dashboard page

## 🔍 Useful Queries

```sql
-- Failures in the last 7 days
SELECT drugs, source, failed_at
FROM failed_drug_lookups
WHERE failed_at > NOW() - INTERVAL '7 days'
ORDER BY failed_at DESC;

-- Most common failing drugs
SELECT drugs, COUNT(*) AS failures
FROM failed_drug_lookups
GROUP BY drugs
ORDER BY failures DESC
LIMIT 20;

-- Breakdown by source
SELECT source, COUNT(*) AS failures
FROM failed_drug_lookups
GROUP BY source
ORDER BY failures DESC;
```

## 🧩 Benefits
- **Proactive monitoring**: Real-time Pushover alerts on every failure.
- **Actionable intelligence**: See exactly which drugs and APIs are failing.
- **Database improvement**: Identify missing drugs to add to the database.
- **API health**: Monitor which external APIs are causing the most issues.
- **Cost optimization**: Track patterns to optimize API usage.
