# Ethiopia Financial Inclusion Forecast

Forecasting Ethiopia's financial-inclusion **Access** and **Usage** indicators from a
sparse, event-annotated time series, using a unified data schema where observations,
events, policy targets and modelled event→indicator impact links share one structure.

## Data model

| record_type | `category` | `pillar` | Meaning |
|-------------|-----------|----------|---------|
| `observation` | — | set | A measured value (survey / operator / regulator) |
| `event` | set | *empty* | A policy, launch or milestone — deliberately **not** pre-assigned to a pillar |
| `impact_link` | — | set | A modelled effect of an event (`parent_id`) on an indicator |
| `target` | — | set | An official policy goal |

Events stay pillar-neutral; their effects are expressed only through `impact_link` records,
which keeps the data unbiased. See `data/README.md` for the full schema.

## Repository layout

```
data/raw/         # faithful CSV of the starter workbook (never edited)
data/processed/   # analysis-ready enriched dataset (generated)
src/              # load_data.py, build_processed_dataset.py
tests/            # data-integrity tests (run in CI)
notebooks/  models/  dashboard/  reports/figures/
```

## Quick start

```bash
pip install -r requirements.txt

# Rebuild the processed dataset (correction + enrichment) from raw
python src/build_processed_dataset.py

# Load & summarise
python -m src.load_data

# Run data-integrity tests
pytest -q
```

## Task 1 — data exploration & enrichment

The starter dataset (57 records) was converted to CSV, one systematic column-alignment
defect was corrected, and 30 sourced records were added (20 observations, 3 events,
7 impact_links), yielding the 87-record processed dataset. Every change — source URL,
exact quote, confidence and rationale — is documented in
[`data_enrichment_log.md`](data_enrichment_log.md).
