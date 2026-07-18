# Notebooks

Exploratory and modelling notebooks for the Ethiopia FI forecast.

Load data via the shared helper so paths stay consistent:

```python
from src.load_data import load_all
data = load_all(processed=True)   # dict: unified, observations, events, targets, impact_links, reference_codes
```

Planned:
- `01_eda.ipynb` — record counts, indicator coverage, temporal gaps, event timeline.
- `02_access_model.ipynb` — ACCESS forecast with event intervention terms.
- `03_usage_model.ipynb` — USAGE forecast (Telebirr adoption curve, P2P volumes).
