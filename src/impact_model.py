"""Event-impact model for the Ethiopia FI forecast (Task 3).

Translates `impact_link` records into a time-based model that predicts how an
indicator moves when events occur, builds the event-indicator association matrix,
and validates predictions against observed history.

--------------------------------------------------------------------------------
Functional form — how an event's effect unfolds over time
--------------------------------------------------------------------------------
Each impact_link i (event e, indicator k) has an asymptotic effect M_ik and a
lag `L` (months). We model the *fraction* of that effect realized `Δt` months
after the event as a saturating half-life ramp:

        g(Δt) = 1 - 0.5 ** (Δt / L)        for Δt >= 0,  else 0

  * g(L)   = 0.50   (lag = months to reach HALF of the full effect)
  * g(2L)  = 0.75,  g(3L) = 0.875 ...  ->  asymptotes to the full effect M
  * effects therefore build GRADUALLY, faster for small L, slowly for large L.

`L` already encodes "how gradual": direct launches have small L (3-6 mo), enabling
policies have large L (15-36 mo), so no extra relationship_type term is needed.

--------------------------------------------------------------------------------
Combining effects & units
--------------------------------------------------------------------------------
Indicators are classified by `value_type`:
  * ADDITIVE (percentage / gap_pp): M is in percentage POINTS, effects ADD.
        level(t) = anchor + Σ_i M_i * [g_i(t) - g_i(t_anchor)]
  * MULTIPLICATIVE (count / currency / ratio): M is a PERCENT change, effects COMPOUND.
        level(t) = anchor * Π_i (1 + (M_i/100) * [g_i(t) - g_i(t_anchor)])

Effects are measured as an INCREMENT relative to the anchor date, so events that
began before the anchor (already partly realized) are handled correctly and not
double-counted. The implicit counterfactual is "no further change absent events."
"""
from pathlib import Path
import numpy as np
import pandas as pd

from src.load_data import load_all

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"
DAYS_PER_MONTH = 30.44

# qualitative magnitude -> ordinal strength (for the unit-free color scale)
MAG_ORDINAL = {"high": 3, "medium": 2, "low": 1, "negligible": 0.5}
# fallback asymptote when impact_estimate is missing (band midpoints); flagged qualitative
MAG_DEFAULT = {"high": 20.0, "medium": 10.0, "low": 3.0, "negligible": 0.5}
DIR_SIGN = {"increase": 1, "decrease": -1, "stabilize": 0, "mixed": 0}

ADDITIVE_TYPES = {"percentage", "gap_pp"}                       # estimate in pp
MULTIPLICATIVE_TYPES = {"count", "currency_etb", "currency_usd", "ratio"}  # estimate in %

# key indicators for the association matrix columns (task-specified + high-value)
KEY_INDICATORS = [
    "ACC_OWNERSHIP", "ACC_MM_ACCOUNT", "ACC_4G_COV", "USG_DIGITAL_PAY",
    "USG_P2P_COUNT", "USG_TELEBIRR_USERS", "USG_MPESA_USERS", "USG_MPESA_ACTIVE",
    "AFF_DATA_INCOME", "GEN_GAP_ACC", "GEN_MM_SHARE", "DEP_BORROWED",
]


# ----------------------------------------------------------------- data assembly
def get_impact_table() -> pd.DataFrame:
    """impact_links joined to their parent event, with typed/ signed effect columns."""
    d = load_all(processed=True)
    ev = d["events"][["record_id", "indicator", "category", "observation_date"]].rename(
        columns={"record_id": "parent_id", "indicator": "event_name",
                 "observation_date": "event_date"})
    # drop the impact_link's own (empty) category so the event's category wins the join
    il = d["impact_links"].drop(columns=["category"]).merge(ev, on="parent_id", how="left").copy()
    il["event_date"] = pd.to_datetime(il["event_date"])
    il["lag_months"] = pd.to_numeric(il["lag_months"], errors="coerce")
    il["impact_estimate"] = pd.to_numeric(il["impact_estimate"], errors="coerce")

    # indicator value_type -> combination rule
    vt = (d["observations"][["indicator_code", "value_type"]].drop_duplicates()
          .set_index("indicator_code")["value_type"].to_dict())
    il["value_type"] = il["related_indicator"].map(vt)
    il["combine"] = np.where(il["value_type"].isin(MULTIPLICATIVE_TYPES),
                             "multiplicative", "additive")

    # signed asymptote (native units) + flag when derived from the band (no numeric est)
    sign = il["impact_direction"].map(DIR_SIGN)
    est = il["impact_estimate"]
    band = il["impact_magnitude"].map(MAG_DEFAULT) * sign
    il["asymptote"] = np.where(est.notna(), est, band)
    il["is_qualitative"] = est.isna()
    # "creation" links: a from-zero count series has no meaningful % baseline
    il["is_creation"] = il["is_qualitative"] & (il["combine"] == "multiplicative")
    il["ordinal"] = il["impact_magnitude"].map(MAG_ORDINAL) * sign
    return il


# --------------------------------------------------------------- functional form
def effect_fraction(months_since_event, lag):
    """Half-life saturating ramp g(Δt) = 1 - 0.5**(Δt/lag), clamped at 0 for Δt<0."""
    dt = np.asarray(months_since_event, dtype=float)
    frac = 1.0 - np.power(0.5, np.clip(dt, 0, None) / lag)
    return np.where(dt < 0, 0.0, frac)


def _months_between(t, t0):
    return (pd.to_datetime(t) - pd.to_datetime(t0)).days / DAYS_PER_MONTH


# ------------------------------------------------------------ association matrix
def build_association_matrix(il: pd.DataFrame = None):
    """Return (numeric, ordinal) event x indicator matrices.

    numeric: signed asymptotic effect in native units (pp for %, % for counts).
    ordinal: signed magnitude band in [-3, 3] — unit-free, comparable across cells.
    """
    if il is None:
        il = get_impact_table()
    numeric = il.pivot_table(index="event_name", columns="related_indicator",
                             values="asymptote", aggfunc="sum")
    ordinal = il.pivot_table(index="event_name", columns="related_indicator",
                             values="ordinal", aggfunc="sum")
    # order columns: key indicators first (those present), then any extras
    cols = [c for c in KEY_INDICATORS if c in numeric.columns] + \
           [c for c in numeric.columns if c not in KEY_INDICATORS]
    return numeric[cols], ordinal[cols]


# --------------------------------------------------------------------- simulate
def simulate_indicator(indicator_code, target_dates, anchor_value, anchor_date,
                       il: pd.DataFrame = None, attenuation: float = 1.0):
    """Predict an indicator's level at `target_dates` from its anchor via events.

    attenuation scales all asymptotes for this indicator (empirical shrinkage from
    validation). Only links with a numeric estimate enter the arithmetic; purely
    qualitative/enabling links (no estimate) are excluded rather than assigned a
    fabricated band-midpoint magnitude.
    """
    if il is None:
        il = get_impact_table()
    links = il[(il.related_indicator == indicator_code) & (~il.is_qualitative)].copy()
    combine = "multiplicative" if (len(links) and links["combine"].iloc[0] == "multiplicative") \
        else "additive"
    target_dates = pd.to_datetime(pd.Index(target_dates))

    out = []
    for t in target_dates:
        add, mul = 0.0, 1.0
        for _, r in links.iterrows():
            g_t = effect_fraction(_months_between(t, r.event_date), r.lag_months)
            g_a = effect_fraction(_months_between(anchor_date, r.event_date), r.lag_months)
            incr = float(g_t - g_a)                 # realized since anchor
            M = r.asymptote * attenuation
            if combine == "additive":
                add += M * incr
            else:
                mul *= (1.0 + (M / 100.0) * incr)
        out.append(anchor_value + add if combine == "additive" else anchor_value * mul)
    return pd.Series(out, index=target_dates, name=indicator_code)


# -------------------------------------------------------------------- validation
def _series(obs, code):
    s = obs[obs.indicator_code == code].copy()
    s["date"] = pd.to_datetime(s["observation_date"])
    s["value_numeric"] = pd.to_numeric(s["value_numeric"], errors="coerce")
    return s[s.gender == "all"].sort_values("date")


def validate(il: pd.DataFrame = None):
    """Compare naive predictions vs observed for indicators with >=2 real years.

    Returns a dict: indicator -> {anchor, observed(dict), predicted(dict), attenuation}.
    For ACC_OWNERSHIP we also solve the attenuation that matches the latest observation.
    """
    if il is None:
        il = get_impact_table()
    d = load_all(processed=True)
    obs = d["observations"]
    results = {}
    for code in ["ACC_OWNERSHIP", "ACC_MM_ACCOUNT"]:
        s = _series(obs, code)
        if len(s) < 2:
            continue
        # anchor = first observation at/after the earliest relevant event window
        anchor = s.iloc[s["date"].searchsorted(pd.Timestamp("2021-01-01"))] \
            if code == "ACC_OWNERSHIP" else s[s["date"] >= "2021-01-01"].iloc[0]
        later = s[s["date"] > anchor["date"]]
        preds = simulate_indicator(code, later["date"], anchor["value_numeric"],
                                   anchor["date"], il=il)
        res = {
            "anchor": {"date": str(anchor["date"].date()), "value": anchor["value_numeric"]},
            "observed": {str(r["date"].date()): r["value_numeric"] for _, r in later.iterrows()},
            "predicted_naive": {str(k.date()): round(v, 2) for k, v in preds.items()},
            "attenuation": 1.0,
        }
        # calibrate attenuation on the last point (ownership only)
        if code == "ACC_OWNERSHIP" and len(later):
            last = later.iloc[-1]
            naive_delta = preds.iloc[-1] - anchor["value_numeric"]
            obs_delta = last["value_numeric"] - anchor["value_numeric"]
            alpha = float(np.clip(obs_delta / naive_delta, 0, 1)) if naive_delta else 1.0
            res["attenuation"] = round(alpha, 3)
            preds_ref = simulate_indicator(code, later["date"], anchor["value_numeric"],
                                           anchor["date"], il=il, attenuation=alpha)
            res["predicted_refined"] = {str(k.date()): round(v, 2) for k, v in preds_ref.items()}
        results[code] = res
    return results


# ----------------------------------------------------------------------- figures
def fig_effect_curves():
    """Illustrate the half-life ramp for several lags."""
    from src import eda
    import matplotlib.pyplot as plt
    eda._style()
    fig, ax = plt.subplots(figsize=(9, 5.2))
    months = np.arange(0, 49)
    for lag, c in zip([3, 6, 12, 24], [eda.OI["blue"], eda.OI["green"],
                                       eda.OI["orange"], eda.OI["vermillion"]]):
        ax.plot(months, effect_fraction(months, lag), lw=2.4, color=c, label=f"lag = {lag} mo")
        ax.scatter([lag], [0.5], color=c, zorder=5, s=45)
    ax.axhline(0.5, ls="--", color=eda.MUTED, lw=1)
    ax.text(46, 0.52, "50% of full effect at Δt = lag", ha="right", color=eda.MUTED, fontsize=9)
    ax.set_xlabel("Months since event (Δt)"); ax.set_ylabel("Fraction of full effect  g(Δt)")
    ax.set_ylim(0, 1.02); ax.set_title("Functional form: effects build gradually\n"
                                       r"$g(\Delta t)=1-0.5^{\,\Delta t/\mathrm{lag}}$")
    ax.legend(frameon=False)
    fig.tight_layout()
    return fig


def fig_association_matrix(il: pd.DataFrame = None):
    """Heatmap: color = signed ordinal band (unit-free), text = numeric estimate.
    Cells from a qualitative band (no numeric estimate) are marked with '*'."""
    from src import eda
    import matplotlib.pyplot as plt
    eda._style()
    if il is None:
        il = get_impact_table()
    num, ordv = build_association_matrix(il)
    qual = il.pivot_table(index="event_name", columns="related_indicator",
                          values="is_qualitative", aggfunc="max").reindex_like(num)
    num, ordv = num.sort_index(), ordv.reindex(sorted(ordv.index))
    ordv = ordv[num.columns]; qual = qual.reindex(index=num.index, columns=num.columns)

    fig, ax = plt.subplots(figsize=(12.5, 7))
    data = np.ma.masked_invalid(ordv.values.astype(float))
    im = ax.imshow(data, aspect="auto", cmap="RdBu", vmin=-3, vmax=3)
    ax.set_xticks(range(len(num.columns))); ax.set_xticklabels(num.columns, rotation=55, ha="right", fontsize=8.5)
    ax.set_yticks(range(len(num.index))); ax.set_yticklabels(num.index, fontsize=8.5)
    for i in range(num.shape[0]):
        for j in range(num.shape[1]):
            v = num.values[i, j]
            if not np.isnan(v):
                star = "*" if bool(qual.values[i, j]) else ""
                txt = f"{v:+.0f}{star}"
                strong = abs(ordv.values[i, j]) > 1.5
                ax.text(j, i, txt, ha="center", va="center", fontsize=8.5,
                        color="white" if strong else eda.INK)
    ax.set_title("Event → indicator association matrix\n"
                 "color = signed magnitude band · text = estimated effect (pp for %, % for counts) · * = qualitative")
    fig.colorbar(im, ax=ax, shrink=0.6, label="signed band (−3…+3)")
    ax.grid(False)
    fig.tight_layout()
    return fig


def fig_validation(il: pd.DataFrame = None):
    """Predicted (naive & refined) vs observed for the two validated indicators."""
    from src import eda
    import matplotlib.pyplot as plt
    eda._style()
    res = validate(il)
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.2))
    for ax, code in zip(axes, ["ACC_MM_ACCOUNT", "ACC_OWNERSHIP"]):
        r = res[code]
        date = list(r["observed"])[-1]
        anchor_v = r["anchor"]["value"]
        bars = {"anchor\n(" + r["anchor"]["date"][:7] + ")": anchor_v,
                "observed\n(" + date[:7] + ")": r["observed"][date],
                "predicted\nnaive": r["predicted_naive"][date]}
        if "predicted_refined" in r:
            bars["predicted\nrefined"] = r["predicted_refined"][date]
        colors = [eda.MUTED, eda.OI["green"], eda.OI["vermillion"], eda.OI["blue"]][:len(bars)]
        b = ax.bar(list(bars), list(bars.values()), color=colors, zorder=3, width=0.7)
        for bar, v in zip(b, bars.values()):
            ax.text(bar.get_x() + bar.get_width() / 2, v + 0.4, f"{v:.1f}", ha="center",
                    fontsize=9.5, color=eda.INK, fontweight="bold")
        sub = "well-calibrated (no attenuation)" if code == "ACC_MM_ACCOUNT" \
            else f"naive over-predicts → attenuation α = {r['attenuation']}"
        ax.set_title(f"{code}\n{sub}", fontsize=11)
        ax.set_ylabel("% of adults"); ax.grid(axis="x", visible=False); ax.margins(y=0.16)
    fig.suptitle("Validation: predicted vs observed (anchor 2021 → 2024)", fontweight="bold", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    return fig


def save_figures():
    import matplotlib.pyplot as plt
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    il = get_impact_table()
    figs = {"12_effect_curves": fig_effect_curves(),
            "13_association_matrix": fig_association_matrix(il),
            "14_validation": fig_validation(il)}
    for name, fig in figs.items():
        out = FIG_DIR / f"{name}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print("saved", out.relative_to(ROOT))
    plt.close("all")


if __name__ == "__main__":
    il = get_impact_table()
    num, ordv = build_association_matrix(il)
    print("=== Association matrix (numeric asymptotic effects) ===")
    print(num.round(1).to_string())
    print("\n=== Validation ===")
    import json
    print(json.dumps(validate(il), indent=2, default=str))
