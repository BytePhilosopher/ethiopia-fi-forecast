"""Model explainability for the Ethiopia FI forecast (Engineering task).

Two complementary views:

1. **Exact additive attribution** of the ownership forecast. The forecast is additive
   (anchor + organic drift + Σ attenuated event effects), so each component's contribution
   is exact — no approximation needed. This answers *why did the model predict this value?*
   and *which events contribute most?* via a waterfall.

2. **SHAP on an ML surrogate.** To answer *which features make an event impactful, globally?*
   we fit a RandomForest that predicts a link's effect magnitude from its features
   (lag, relationship type, evidence basis, event category, affected pillar) and explain it
   with SHAP.

   Two caveats are load-bearing, not boilerplate:

   * **Unit coherence.** ``impact_estimate`` is only comparable within a ``value_type``: a
     ``percentage`` row is percentage points, while a ``count`` row is a *percent growth*
     in a transaction count. Regressing across both would compare pp against %-growth, so
     the surrogate is fitted on the additive (pp-denominated) links only —
     ``IMPACT_CFG.additive_types``, the same set the impact engine adds rather than
     multiplies. This drops the sample to ~13 rows.
   * **Sample size.** Those rows are a curated knowledge base, not a random sample, so the
     ranking is *illustrative* and leverage-sensitive: a handful of records can move it.
     :func:`shap_importance` is therefore the single source of truth for the ranking shown
     in the report and the dashboard, and the tests assert SHAP's structural guarantees
     (additivity, determinism) rather than a specific winning feature.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import forecast as fc
from src import impact_model as im
from src.config import FORECAST_CFG, IMPACT_CFG
from src.utils import PALETTE, half_life_fraction, months_between

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"

OWNERSHIP = "ACC_OWNERSHIP"
SURROGATE_FEATURES = ["lag_months", "relationship_type", "evidence_basis",
                      "category", "pillar"]


# =====================================================================================
# 1. Exact additive attribution of the ownership forecast
# =====================================================================================
def ownership_contributions(scenario: str = "base", year: int | None = None) -> pd.DataFrame:
    """Decompose a scenario's ownership forecast into additive pp contributions.

    Returns rows for the anchor, organic drift, and each event's attenuated increment
    between the anchor date and the target year — which sum exactly to the forecast.
    """
    year = year or FORECAST_CFG.forecast_years[-1]
    scen = FORECAST_CFG.ownership_scenarios[scenario]
    anchor_val = FORECAST_CFG.ownership_anchor
    anchor_date = FORECAST_CFG.anchor_date
    target_date = pd.Timestamp(f"{year}-12-31")

    il = im.get_impact_table()
    links = il[(il.related_indicator == OWNERSHIP) & (~il.is_qualitative)]

    rows = [{"component": "Anchor (2024 observed)", "kind": "anchor", "pp": anchor_val}]
    organic = scen.organic_drift_pp_per_year * (target_date - anchor_date).days / 365.25
    rows.append({"component": "Organic drift", "kind": "organic", "pp": organic})
    for _, r in links.iterrows():
        g_t = float(half_life_fraction(months_between(target_date, r.event_date), r.lag_months))
        g_a = float(half_life_fraction(months_between(anchor_date, r.event_date), r.lag_months))
        contrib = r.asymptote * scen.event_attenuation * (g_t - g_a)
        rows.append({"component": r.event_name, "kind": "event", "pp": float(contrib)})

    df = pd.DataFrame(rows)
    df["forecast_total"] = df["pp"].sum()
    return df


def fig_attribution_waterfall(scenario: str = "base", year: int | None = None) -> "plt.Figure":
    """Waterfall: how the anchor, drift and each event build up the forecast."""
    import matplotlib.pyplot as plt
    from src import eda
    eda._style()
    df = ownership_contributions(scenario, year)
    year = year or FORECAST_CFG.forecast_years[-1]

    labels = list(df["component"]) + ["Forecast total"]
    pps = list(df["pp"]) + [0.0]
    running = np.cumsum([0.0] + list(df["pp"]))[:-1]
    fig, ax = plt.subplots(figsize=(10.5, 6))
    for i, (lab, pp, base) in enumerate(zip(df["component"], df["pp"], running)):
        kind = df["kind"].iloc[i]
        color = {"anchor": PALETTE.muted, "organic": PALETTE.sky}.get(kind, PALETTE.blue)
        if kind == "event":
            color = PALETTE.green if pp >= 0 else PALETTE.vermillion
        ax.bar(i, pp, bottom=base, color=color, zorder=3, width=0.66)
        ax.text(i, base + pp + 0.15, f"{pp:+.1f}", ha="center", fontsize=8.5, color=PALETTE.ink)
    total = df["forecast_total"].iloc[0]
    ax.bar(len(df), total, color=PALETTE.black, zorder=3, width=0.66)
    ax.text(len(df), total + 0.15, f"{total:.1f}", ha="center", fontsize=9.5,
            fontweight="bold", color=PALETTE.ink)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8.5)
    ax.set_ylabel("Account ownership (% of adults)")
    ax.set_title(f"Why the model predicts {total:.1f}% ownership in {year} ({scenario} case)\n"
                 "exact additive attribution: anchor + drift + each event's effect")
    ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


def global_event_importance(scenario: str = "base") -> pd.DataFrame:
    """Rank events by absolute pp contribution to the forecast (global importance)."""
    df = ownership_contributions(scenario)
    ev = df[df["kind"] == "event"].copy()
    ev["abs_pp"] = ev["pp"].abs()
    return ev.sort_values("abs_pp", ascending=False)[["component", "pp"]].reset_index(drop=True)


# =====================================================================================
# 2. SHAP on an ML surrogate (what makes an event impactful?)
# =====================================================================================
def build_feature_frame() -> tuple[pd.DataFrame, pd.Series, pd.DataFrame]:
    """Return (X_encoded, y, raw_features) for links with a pp-denominated estimate.

    Target ``y`` = absolute effect magnitude ``|impact_estimate|`` in percentage points.
    Restricted to ``IMPACT_CFG.additive_types`` so every row shares one unit — a ``count``
    row's estimate is a percent *growth*, which is not comparable with a pp effect and
    would otherwise dominate the regression for purely dimensional reasons.
    """
    il = im.get_impact_table()
    d = il[(~il.is_qualitative) & (il.value_type.isin(IMPACT_CFG.additive_types))].copy()
    raw = d[SURROGATE_FEATURES].copy()
    raw["lag_months"] = pd.to_numeric(raw["lag_months"], errors="coerce")
    y = d["impact_estimate"].abs().reset_index(drop=True)
    X = pd.get_dummies(raw, columns=["relationship_type", "evidence_basis",
                                     "category", "pillar"], dtype=float)
    X = X.reset_index(drop=True)
    return X, y, raw.reset_index(drop=True)


def train_surrogate(random_state: int = 0) -> tuple["RandomForestRegressor", pd.DataFrame, pd.Series]:
    """Fit a RandomForest surrogate that predicts effect magnitude from link features."""
    from sklearn.ensemble import RandomForestRegressor
    X, y, _ = build_feature_frame()
    model = RandomForestRegressor(n_estimators=300, max_depth=4,
                                  random_state=random_state)
    model.fit(X, y)
    return model, X, y


def shap_explanation(random_state: int = 0) -> tuple[np.ndarray, pd.DataFrame,
                                                     "RandomForestRegressor", "shap.TreeExplainer"]:
    """Return (shap_values, X, model) using SHAP's TreeExplainer."""
    import shap
    model, X, y = train_surrogate(random_state)
    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(X)
    return values, X, model, explainer


def shap_importance(random_state: int = 0) -> pd.DataFrame:
    """Global feature ranking by mean |SHAP|, descending.

    The single source of truth for the ranking quoted in the report and rendered by the
    dashboard, so the narrative can never drift from the model's actual output.
    """
    values, X, _, _ = shap_explanation(random_state)
    imp = pd.DataFrame({"feature": X.columns,
                        "mean_abs_shap": np.abs(values).mean(axis=0)})
    return imp.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def fig_shap_global(random_state: int = 0) -> "plt.Figure":
    """Global feature importance (mean |SHAP|) — which features drive impact magnitude."""
    import matplotlib.pyplot as plt
    import shap
    plt.close("all")  # SHAP draws on the current figure — start from a clean slate
    values, X, _, _ = shap_explanation(random_state)
    shap.summary_plot(values, X, plot_type="bar", show=False, max_display=10)
    fig = plt.gcf()
    fig.set_size_inches(10, 6)
    fig.suptitle("Which features make an event impactful? (mean |SHAP|)",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


def fig_shap_beeswarm(random_state: int = 0) -> "plt.Figure":
    """Beeswarm — direction of each feature's effect on predicted magnitude."""
    import matplotlib.pyplot as plt
    import shap
    plt.close("all")
    values, X, _, _ = shap_explanation(random_state)
    shap.summary_plot(values, X, show=False, max_display=10)
    fig = plt.gcf()
    fig.set_size_inches(10, 6)
    fig.suptitle("How each feature shifts predicted impact (SHAP beeswarm)",
                 fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


def save_figures() -> None:
    """Save each figure immediately and close it, so SHAP's global figure state
    never leaks between plots."""
    import matplotlib.pyplot as plt
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    builders = [("17_attribution_waterfall", lambda: fig_attribution_waterfall("base")),
                ("18_shap_global", fig_shap_global),
                ("19_shap_beeswarm", fig_shap_beeswarm)]
    for name, build in builders:
        fig = build()
        out = FIG_DIR / f"{name}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close("all")
        print("saved", out.relative_to(ROOT))


if __name__ == "__main__":
    print("=== Ownership forecast attribution (base, 2027) ===")
    print(ownership_contributions("base").round(2).to_string(index=False))
    print("\n=== Global event importance ===")
    print(global_event_importance().round(2).to_string(index=False))
    print("\n=== SHAP global feature importance ===")
    print(shap_importance().round(3).to_string(index=False))
    print()
    save_figures()
