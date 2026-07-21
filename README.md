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

# Regenerate EDA figures, then rebuild + execute the EDA notebook
python src/eda.py
python src/build_notebook.py
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb

# Run tests (data integrity + EDA smoke)
pytest -q
```

## Task 1 — data exploration & enrichment

The starter dataset (57 records) was converted to CSV, one systematic column-alignment
defect was corrected, and 30 sourced records were added (20 observations, 3 events,
7 impact_links), yielding the 87-record processed dataset. Every change — source URL,
exact quote, confidence and rationale — is documented in
[`data_enrichment_log.md`](data_enrichment_log.md).

## Task 2 — exploratory data analysis

[`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) explores composition, temporal coverage,
data quality, the access-ownership plateau, the registered-vs-active usage paradox, the
gender gap, and event/impact relationships (figures in [`reports/figures/`](reports/figures/)).
Findings are written up in [`reports/eda_key_insights.md`](reports/eda_key_insights.md)
(6 insights + hypotheses) and [`reports/data_quality_assessment.md`](reports/data_quality_assessment.md).
An interim report combining Tasks 1–2 is at [`reports/interim_report.md`](reports/interim_report.md).

## Task 3 — event impact modeling

[`notebooks/02_impact_model.ipynb`](notebooks/02_impact_model.ipynb) (engine
[`src/impact_model.py`](src/impact_model.py)) turns `impact_link` records into a time-based model
— a half-life effect ramp `g(Δt)=1−0.5^(Δt/lag)`, additive (pp) vs multiplicative (%) combination
by indicator unit — builds the [event→indicator association matrix](reports/figures/13_association_matrix.png),
and validates it: ACC_MM_ACCOUNT is well-calibrated (8.9% vs 9.45% observed) while ACC_OWNERSHIP
over-predicts (62.7% vs 49%) and needs attenuation α≈0.18. Methodology, sources, validation and
uncertainties: [`reports/impact_model_methodology.md`](reports/impact_model_methodology.md).

## Task 4 — forecasting Access & Usage (2025–2027)

[`notebooks/03_forecast.ipynb`](notebooks/03_forecast.ipynb) (engine [`src/forecast.py`](src/forecast.py))
forecasts account ownership and digital-payment usage with linear-trend + 95% PI, an
event-augmented scenario model (pessimistic/base/optimistic), and an ownership × payment-propensity
decomposition for the single-point digital-payment target. Base case: ownership **~54% by 2027**
(band 51–58%, short of the NFIS-II 70% target), digital payments **~27%** (band 23–32%). Table:
[`data/processed/forecasts_2025_2027.csv`](data/processed/forecasts_2025_2027.csv); interpretation:
[`reports/forecast_interpretation.md`](reports/forecast_interpretation.md).

## Task 5 — interactive dashboard

[`dashboard/app.py`](dashboard/app.py) is a Streamlit app (interactive Plotly charts, same
colorblind-safe palette) with four pages:

- **Overview** — metric cards, the P2P/ATM crossover gauge, and the growth-deceleration chart.
- **Trends** — multi-indicator time series with indicator picker + year-range slider, and a
  channel-comparison view (P2P vs ATM, Telebirr vs M-Pesa), with a data-download button.
- **Forecasts** — ownership & digital-payment forecasts with confidence intervals, a model
  selector (event-augmented scenarios / linear trend+PI / both), projected milestones, the
  event→indicator association heatmap, and a forecast-table download.
- **Inclusion Projections** — projection with a scenario selector, a progress-toward-60%-target
  gauge, and expandable answers to the consortium's key questions.

### Run the dashboard locally

```bash
pip install -r requirements.txt          # includes streamlit + plotly
streamlit run dashboard/app.py           # opens http://localhost:8501
```

The app reuses the analysis engines in `src/` (no separate data prep needed). Pure data helpers
live in [`dashboard/data_access.py`](dashboard/data_access.py); the app is smoke-tested via
Streamlit's `AppTest` in [`tests/test_dashboard.py`](tests/test_dashboard.py).
