"""Assemble + execute notebooks/03_forecast.ipynb.  Run: python src/build_forecast_notebook.py"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "03_forecast.ipynb"
md, code = new_markdown_cell, new_code_cell

cells = [
    md("# Forecasting Access & Usage, 2025–2027 (Task 4)\n"
       "\n"
       "**Author:** Yostina Abera  \n"
       "**Targets:** `ACC_OWNERSHIP` (account ownership, % adults) and `USG_DIGITAL_PAY` "
       "(made/received a digital payment, % adults).  \n"
       "**Engine:** `src/forecast.py` (builds on the Task-3 impact model). Interpretation: "
       "`reports/forecast_interpretation.md`.\n"
       "\n"
       "The data is sparse (account ownership has **4 Findex points over 13 years**; digital "
       "payments have **one**). So we combine three methods: a linear trend with a prediction "
       "interval (statistical uncertainty), an **event-augmented scenario** model (the central "
       "forecast), and a scenario band (structural uncertainty)."),

    code("import sys; from pathlib import Path\n"
         "sys.path.insert(0, str(Path.cwd().parent))\n"
         "import pandas as pd, numpy as np\n"
         "%matplotlib inline\n"
         "from src import forecast as fc\n"
         "pd.set_option('display.width', 200)"),

    md("## 1. Targets and available history\n"
       "Account ownership has a usable trend; digital payments do not — a limitation we carry "
       "throughout."),
    code("own = fc.ownership_series()\n"
         "print('ACC_OWNERSHIP history:'); print(own.to_string(index=False))\n"
         "print(f'\\nUSG_DIGITAL_PAY: single point = {fc.DP_ANCHOR}% (2024); '\n"
         "      f'implied payment-propensity = {fc.DP_PROPENSITY_0:.3f} of account-holders')"),

    md("## 2. Method 1 — linear trend continuation (+ 95% prediction interval)\n"
       "Ordinary least squares on the 4 points, with a t-based prediction interval (2 d.f.). "
       "Honest, but it **ignores the observed deceleration** (+13, +11, +3 pp between surveys) so "
       "it tends to over-forecast; the interval is very wide because n=4."),
    code("lin, params = fc.linear_trend(own)\n"
         "print(f\"slope = {params['slope']:.2f} pp/yr,  residual s = {params['resid_std']:.2f}\")\n"
         "lin.round(1)"),

    md("## 3. Method 2 — event-augmented scenario model (central forecast)\n"
       "Anchor at the 2024 observation and add (a) an **organic drift** (non-event pp/yr) and "
       "(b) **attenuated event effects** from the Task-3 impact model (`simulate_indicator`). "
       "Scenarios vary the drift and the event attenuation α:\n"
       "\n"
       "| scenario | organic drift | event α | rationale |\n"
       "|---|---|---|---|\n"
       "| pessimistic | 0.5 pp/yr | 0.10 | the 2021–24 near-stall continues |\n"
       "| base | 1.2 pp/yr | 0.18 | ≈ recent rate; α = Task-3 validated value |\n"
       "| optimistic | 2.0 pp/yr | 0.30 | device adoption + events accelerate |\n"),
    code("own_scen = fc.ownership_scenarios()\n"
         "own_scen.round(1)"),

    md("## 4. Method 3 — digital payments as ownership × payment-propensity\n"
       "With only one Findex point, we project digital payments as `ownership × propensity`, where "
       "propensity (share of account-holders paying digitally, 0.43 in 2024) is the scenario lever. "
       "Rising propensity is corroborated by **P2P transactions +158% YoY** (49.7M→128.3M) and the "
       "interoperability events (EthioPay, M-Pesa–EthSwitch)."),
    code("dp_scen = fc.digital_pay_scenarios()\n"
         "dp_scen.round(1)"),

    md("## 5. Forecast table with confidence intervals\n"
       "`base` is the central forecast; `[pessimistic, optimistic]` is the scenario band; for "
       "ownership the linear 95% PI is shown alongside. Saved to "
       "`data/processed/forecasts_2025_2027.csv`."),
    code("table = fc.save_table()\n"
         "table"),

    md("## 6. Scenario visualizations"),
    code("_ = fc.fig_ownership_forecast()"),
    code("_ = fc.fig_digital_pay_forecast()"),

    md("## 7. Interpretation\n"
       "Full write-up: `reports/forecast_interpretation.md`.\n"
       "\n"
       "**What the model predicts.** Account ownership reaches **~54% by 2027** (base; band "
       "51–58%), continuing the *deceleration* — not the linear extrapolation to ~60%. Digital "
       "payments grow faster off a low base to **~27% by 2027** (base; band 23–32%), because the "
       "usage frontier (transacting) is moving even though the access frontier (owning an account) "
       "has largely saturated.\n"
       "\n"
       "**The NFIS-II 70% ownership target (2025) is unreachable** — it would require +21pp in a "
       "year against an observed +1pp/yr. Even the optimistic path is ~58% by 2027.\n"
       "\n"
       "**Events with the largest potential impact.** On *usage*: interoperability (EthioPay, "
       "M-Pesa–EthSwitch) and the digital-payments strategy — they raise payment propensity. On "
       "*access*: Fayda digital ID and (long-lag) foreign-bank entry — but their ownership effect "
       "is attenuated (α≈0.18) because, as Task 3 showed, new rails mostly digitise the "
       "already-banked rather than create new account-holders.\n"
       "\n"
       "**Key uncertainties.** (1) Digital payments rest on a single data point — the widest band. "
       "(2) The attenuation α is calibrated on one interval. (3) Long-lag policies (foreign banks, "
       "NFIS-II) are not yet observable. (4) The binding constraint is demand-side device access "
       "(phone 41%, smartphone 40%); if that gap does not close, even the base ownership path is "
       "optimistic."),
]

nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"}})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print("wrote", OUT.relative_to(ROOT), f"({len(cells)} cells)")
