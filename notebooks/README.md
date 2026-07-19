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

Planned:
- `02_access_model.ipynb` — ACCESS forecast with event intervention terms.
- `03_usage_model.ipynb` — USAGE forecast (Telebirr adoption curve, P2P volumes).
