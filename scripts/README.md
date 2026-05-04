# scripts/

Standalone Python utilities. Not part of the API runtime, not part of the CDK app — these are corpus / data-prep / one-off operational tools.

## Why standalone?

Different deps, different lifecycle. The API and CDK have strict prod requirements; these scripts can pip-install whatever they need and don't ship anywhere.

## Setup

```bash
cd scripts
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt   # add a requirements.txt only if a script needs deps beyond stdlib
```

Most scripts here use stdlib only.

## Current scripts

### `extract_independent_claims.py`

Parses a Google Patents BigQuery JSON export into one-record-per-patent JSONL of independent claims, plus a sampled human-review file.

**Input:** `data_cache/patents_500.json` (BigQuery `SELECT * FROM patents-public-data.patents.publications WHERE ...` exported as JSON)

**Outputs:**
- `data_cache/independent_claims.jsonl` — full corpus, one patent per line
- `data_cache/sample_for_mining.txt` — random sample of 40 AV-tight patents (CPC B60W30/40/50/60, G05D1, G08G1) formatted for human reading

**Run:**
```bash
python scripts/extract_independent_claims.py
```

The data files live under `data_cache/` which is gitignored — bulk data never gets committed.

### How to refresh the corpus

1. Open BigQuery Console (https://console.cloud.google.com/bigquery)
2. Run the SQL in `docs/seed-corpus.md` (or refine the CPC filter)
3. Save results → JSON (local file)
4. Move the file to `data_cache/patents_500.json`
5. `python scripts/extract_independent_claims.py`
