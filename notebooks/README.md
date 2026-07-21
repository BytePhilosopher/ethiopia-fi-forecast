# Notebooks

Exploratory and modelling notebooks for the Ethiopia FI forecast.

Load data via the shared helper so paths stay consistent:

```python
from src.load_data import load_all
data = load_all(processed=True)   # dict: unified, observations, events, targets, impact_links, reference_codes
```

- `01_eda.ipynb` — **(Task 2, done)** dataset overview, temporal-coverage heatmap, data
  quality, access trajectory + growth deceleration, gender gap, the registered-vs-active
  usage paradox, P2P-vs-ATM crossover, enablers, event timeline, and the impact-link
  relationship matrix. Figures come from `src/eda.py`; regenerate with
  `python src/build_notebook.py && jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda.ipynb`.
  Written findings: [`reports/eda_key_insights.md`](../reports/eda_key_insights.md) and
  [`reports/data_quality_assessment.md`](../reports/data_quality_assessment.md).

- `02_impact_model.ipynb` — **(Task 3, done)** turns `impact_link` records into a time-based
  model (half-life ramp `g(Δt)=1−0.5^(Δt/lag)`), builds the event→indicator association matrix,
  and validates predictions vs observed history (ACC_MM_ACCOUNT well-calibrated; ACC_OWNERSHIP
  over-predicts → α≈0.18). Engine: `src/impact_model.py`; regenerate with
  `python src/build_impact_notebook.py && jupyter nbconvert --to notebook --execute --inplace notebooks/02_impact_model.ipynb`.
  Methodology: [`reports/impact_model_methodology.md`](../reports/impact_model_methodology.md).

Planned:
- `03_access_usage_forecast.ipynb` — ACCESS & USAGE forecasts with event intervention terms.
