"""Forecasting Access & Usage for 2025-2027 (Task 4).

Two targets:
  * ACC_OWNERSHIP   — account ownership, % of adults      (4 Findex points, 2014-2024)
  * USG_DIGITAL_PAY — made/received a digital payment, %  (1 point, 2024 -> anchored)

Three complementary methods, reflecting the sparse, decelerating data:
  1. Linear trend continuation with a 95% prediction interval (statistical uncertainty).
     Honest but ignores the observed saturation -> tends to over-forecast.
  2. Event-augmented scenario model: anchor at the last observation, add organic drift plus
     attenuated event effects from the Task-3 impact model (src/impact_model). This is the
     central ("base") forecast; optimistic/pessimistic vary the organic drift and the event
     attenuation α.
  3. Digital payments are decomposed as ownership × payment-propensity, since only one Findex
     point exists; propensity growth is the scenario lever (corroborated by P2P +158% YoY).

Uncertainty is expressed two ways: the linear 95% PI (statistical) and the optimistic-
pessimistic scenario band (structural / assumption uncertainty).
"""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

if TYPE_CHECKING:                      # import cost avoided at runtime
    from matplotlib.axes import Axes

from src.load_data import load_all
from src import impact_model as im
from src.config import FORECAST_CFG
from src.utils import observation_series, years_between

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"
PROC_DIR = ROOT / "data" / "processed"

# Constants and scenario assumptions come from the typed config (src/config.py);
# re-exported here (in the historical dict shape) for callers/tests.
FORECAST_YEARS: list[int] = list(FORECAST_CFG.forecast_years)
_ANCHOR_DATE: pd.Timestamp = FORECAST_CFG.anchor_date          # Findex 2024 fieldwork
OWN_ANCHOR: float = FORECAST_CFG.ownership_anchor
DP_ANCHOR: float = FORECAST_CFG.digital_pay_anchor
DP_PROPENSITY_0: float = FORECAST_CFG.base_propensity_2024     # 0.429 pay digitally (2024)
OWN_SCENARIOS: dict[str, dict[str, float]] = {
    name: {"drift": s.organic_drift_pp_per_year, "alpha": s.event_attenuation}
    for name, s in FORECAST_CFG.ownership_scenarios.items()}
DP_PROPENSITY: dict[str, dict[int, float]] = FORECAST_CFG.digital_pay_propensity


# ----------------------------------------------------------------- data helpers
def ownership_series() -> pd.DataFrame:
    """Account-ownership Findex history as a tidy (year, value) frame."""
    obs = load_all(processed=True)["observations"]
    s = observation_series(obs, "ACC_OWNERSHIP")
    return s[["year", "value"]].reset_index(drop=True)


# ------------------------------------------------- method 1: linear trend + PI
def linear_trend(series: pd.DataFrame, years: list[int] = FORECAST_YEARS,
                 conf: float = FORECAST_CFG.prediction_interval
                 ) -> tuple[pd.DataFrame, dict[str, float]]:
    """OLS linear fit with a two-sided prediction interval (t, n-2 df)."""
    from scipy import stats
    x = series["year"].to_numpy(float)
    y = series["value"].to_numpy(float)
    n = len(x)
    b, a = np.polyfit(x, y, 1)                 # slope, intercept
    yhat = a + b * x
    sse = float(np.sum((y - yhat) ** 2))
    s = np.sqrt(sse / (n - 2))
    xbar = x.mean(); sxx = float(np.sum((x - xbar) ** 2))
    tcrit = stats.t.ppf(1 - (1 - conf) / 2, df=n - 2)
    rows = []
    for yr in years:
        pred = a + b * yr
        se = s * np.sqrt(1 + 1 / n + (yr - xbar) ** 2 / sxx)
        rows.append({"year": yr, "value": pred, "lo": pred - tcrit * se,
                     "hi": pred + tcrit * se})
    return pd.DataFrame(rows), {"slope": b, "intercept": a, "resid_std": s}


# ---------------------------------------- method 2: event-augmented scenarios
def ownership_scenarios(years: list[int] = FORECAST_YEARS) -> pd.DataFrame:
    """anchor + organic drift + attenuated event increments (per scenario)."""
    il = im.get_impact_table()
    dates = [pd.Timestamp(f"{y}-12-31") for y in years]
    out = {}
    for name, p in OWN_SCENARIOS.items():
        ev = im.simulate_indicator("ACC_OWNERSHIP", dates, OWN_ANCHOR, _ANCHOR_DATE,
                                   il=il, attenuation=p["alpha"])
        vals = []
        for yr, d in zip(years, dates):
            organic = p["drift"] * years_between(d, _ANCHOR_DATE)
            vals.append(float(ev.loc[d] + organic))
        out[name] = pd.Series(vals, index=years)
    return pd.DataFrame(out)


# --------------------------------- method 3: digital payments = ownership × propensity
def digital_pay_scenarios(years: list[int] = FORECAST_YEARS) -> pd.DataFrame:
    own = ownership_scenarios(years)
    out = {}
    for name in OWN_SCENARIOS:
        prop = pd.Series(DP_PROPENSITY[name])
        out[name] = (own[name] * prop).astype(float)
    return pd.DataFrame(out)


# ----------------------------------------------------------------- combined table
def forecast_table() -> pd.DataFrame:
    own = ownership_scenarios()
    dp = digital_pay_scenarios()
    lin, _ = linear_trend(ownership_series())
    rows = []
    for yr in FORECAST_YEARS:
        rows.append({"target": "ACC_OWNERSHIP", "year": yr,
                     "base": round(own.loc[yr, "base"], 1),
                     "pessimistic": round(own.loc[yr, "pessimistic"], 1),
                     "optimistic": round(own.loc[yr, "optimistic"], 1),
                     "linear_trend": round(float(lin.set_index("year").loc[yr, "value"]), 1),
                     "linear_lo95": round(float(lin.set_index("year").loc[yr, "lo"]), 1),
                     "linear_hi95": round(float(lin.set_index("year").loc[yr, "hi"]), 1)})
    for yr in FORECAST_YEARS:
        rows.append({"target": "USG_DIGITAL_PAY", "year": yr,
                     "base": round(dp.loc[yr, "base"], 1),
                     "pessimistic": round(dp.loc[yr, "pessimistic"], 1),
                     "optimistic": round(dp.loc[yr, "optimistic"], 1),
                     "linear_trend": np.nan, "linear_lo95": np.nan, "linear_hi95": np.nan})
    return pd.DataFrame(rows)


def save_table() -> pd.DataFrame:
    PROC_DIR.mkdir(parents=True, exist_ok=True)
    t = forecast_table()
    out = PROC_DIR / "forecasts_2025_2027.csv"
    t.to_csv(out, index=False)
    print("saved", out.relative_to(ROOT))
    return t


# ----------------------------------------------------------------------- figures
def _forecast_axis(ax: "Axes", hist_years: Sequence[float], hist_vals: Sequence[float],
                   scen_df: pd.DataFrame, lin_df: pd.DataFrame | None, anchor: float,
                   title: str, ylabel: str, target_line: float | None = None,
                   target_label: str | None = None) -> None:
    from src import eda
    ax.plot(hist_years, hist_vals, "-o", color=eda.INK, lw=2.4, markersize=8,
            zorder=6, label="observed (Findex)")
    # linear trend + PI band (ownership only)
    if lin_df is not None:
        yrs = lin_df["year"]
        ax.plot(yrs, lin_df["value"], ls="--", color=eda.MUTED, lw=1.6, label="linear trend")
        ax.fill_between(yrs, lin_df["lo"], lin_df["hi"], color=eda.MUTED, alpha=0.12,
                        label="linear 95% PI")
    # scenarios
    colz = {"optimistic": eda.OI["green"], "base": eda.OI["blue"], "pessimistic": eda.OI["vermillion"]}
    x0 = hist_years[-1]
    for name in ["optimistic", "base", "pessimistic"]:
        xs = [x0] + list(scen_df.index)
        ys = [anchor] + list(scen_df[name].values)
        ax.plot(xs, ys, "-o", color=colz[name], lw=2.2, markersize=6, label=name)
        ax.annotate(f"{scen_df[name].iloc[-1]:.0f}", (xs[-1], ys[-1]),
                    textcoords="offset points", xytext=(8, 0), color=colz[name],
                    fontsize=9.5, fontweight="bold", va="center")
    if target_line is not None:
        ax.axhline(target_line, ls=":", color=eda.OI["orange"], lw=1.4)
        ax.text(hist_years[0], target_line + 1, target_label, color=eda.OI["orange"], fontsize=9)
    ax.set_title(title); ax.set_ylabel(ylabel); ax.set_xlabel("Year")
    ax.grid(axis="x", visible=False)


def fig_ownership_forecast() -> "plt.Figure":
    from src import eda
    import matplotlib.pyplot as plt
    eda._style()
    s = ownership_series()
    scen = ownership_scenarios()
    lin, _ = linear_trend(s)
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _forecast_axis(ax, list(s["year"]), list(s["value"]), scen, lin, OWN_ANCHOR,
                   "Account ownership forecast, 2025–2027", "% of adults (15+)",
                   target_line=70, target_label="NFIS-II target 70% (2025) — unreachable")
    ax.legend(loc="upper left", frameon=False, ncol=2, fontsize=9)
    ax.set_ylim(18, 88)
    fig.tight_layout()
    return fig


def fig_digital_pay_forecast() -> "plt.Figure":
    from src import eda
    import matplotlib.pyplot as plt
    eda._style()
    scen = digital_pay_scenarios()
    fig, ax = plt.subplots(figsize=(10.5, 6))
    _forecast_axis(ax, [2024], [DP_ANCHOR], scen, None, DP_ANCHOR,
                   "Digital-payment usage forecast, 2025–2027\n(anchored on one Findex point → wide bands)",
                   "% of adults (15+)")
    ax.legend(loc="upper left", frameon=False, fontsize=9)
    ax.set_ylim(15, 40)
    ax.set_xticks([2024, 2025, 2026, 2027])
    ax.text(0.99, 0.04, "decomposed as ownership × payment-propensity",
            transform=ax.transAxes, ha="right", color=eda.MUTED, fontsize=8.5)
    fig.tight_layout()
    return fig


def save_figures() -> None:
    import matplotlib.pyplot as plt
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    for name, fig in {"15_ownership_forecast": fig_ownership_forecast(),
                      "16_digital_pay_forecast": fig_digital_pay_forecast()}.items():
        out = FIG_DIR / f"{name}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print("saved", out.relative_to(ROOT))
    plt.close("all")


if __name__ == "__main__":
    print(save_table().to_string(index=False))
    print()
    lin, params = linear_trend(ownership_series())
    print("Linear trend slope: %.2f pp/yr" % params["slope"])
    print(lin.round(1).to_string(index=False))
    print()
    save_figures()
