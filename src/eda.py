"""EDA figure-generation engine for the Ethiopia FI forecast (Task 2).

Each `fig_*` function builds one figure and returns a matplotlib Figure. `main()`
saves them all to reports/figures/ at 150 dpi. The notebook imports these functions
so the notebook narrative and the saved figures never diverge.

Design (per the dataviz method):
  * categorical hues = Okabe-Ito (colorblind-safe by construction), fixed order
  * NO dual-axis charts — two scales become small multiples or indexed series
  * sequential single-hue ramp for the coverage heatmap
  * legend for >=2 series, selective direct labels, recessive grid/axes
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import matplotlib.dates as mdates

from src.load_data import load_all

ROOT = Path(__file__).resolve().parents[1]
FIG_DIR = ROOT / "reports" / "figures"

# --- Okabe-Ito colorblind-safe categorical palette (fixed order) ---
OI = {
    "black": "#000000", "orange": "#E69F00", "sky": "#56B4E9", "green": "#009E73",
    "yellow": "#F0E442", "blue": "#0072B2", "vermillion": "#D55E00", "purple": "#CC79A7",
}
CYCLE = [OI["blue"], OI["orange"], OI["green"], OI["vermillion"], OI["purple"],
         OI["sky"], OI["black"], OI["yellow"]]
INK = "#1a1a1a"
MUTED = "#6b6b6b"
GRID = "#e6e6e6"

# category -> color for the event timeline (fixed assignment)
EVENT_COLORS = {
    "product_launch": OI["blue"], "market_entry": OI["orange"], "policy": OI["green"],
    "regulation": OI["purple"], "infrastructure": OI["vermillion"],
    "partnership": OI["sky"], "milestone": OI["black"], "pricing": OI["yellow"],
}


def _style():
    plt.rcParams.update({
        "figure.facecolor": "white", "axes.facecolor": "white",
        "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK,
        "xtick.color": MUTED, "ytick.color": MUTED, "axes.grid": True,
        "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False,
        "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold",
        "figure.dpi": 110,
    })


def _load():
    d = load_all(processed=True)
    obs = d["observations"].copy()
    obs["year"] = pd.to_datetime(obs["observation_date"]).dt.year
    obs["date"] = pd.to_datetime(obs["observation_date"])
    obs["value_numeric"] = pd.to_numeric(obs["value_numeric"], errors="coerce")
    return d, obs


def _series(obs, code, gender="all"):
    s = obs[(obs.indicator_code == code) & (obs.gender == gender)]
    return s.sort_values("date")


# ---------------------------------------------------------------- 1. overview
def fig_overview(d):
    _style()
    u = d["unified"]
    fig, ax = plt.subplots(2, 2, figsize=(11, 7.5))
    fig.suptitle("Dataset overview — composition & quality", fontweight="bold", fontsize=14)

    def barh(a, counts, title, color):
        counts = counts.sort_values()
        a.barh(counts.index, counts.values, color=color, zorder=3)
        for y, v in enumerate(counts.values):
            a.text(v + max(counts.values) * 0.01, y, str(int(v)), va="center", color=INK, fontsize=10)
        a.set_title(title); a.grid(axis="y", visible=False)
        a.margins(x=0.15)

    barh(ax[0, 0], u.record_type.value_counts(), "Records by type", OI["blue"])
    barh(ax[0, 1], u[u.pillar.notna()].pillar.value_counts(), "Records by pillar", OI["green"])
    barh(ax[1, 0], u.source_type.value_counts(), "Records by source type", OI["orange"])
    # confidence with a fixed severity-like order
    conf = u.confidence.value_counts().reindex(["high", "medium", "low", "estimated"]).dropna()
    barh(ax[1, 1], conf, "Records by confidence", OI["purple"])
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    return fig


# --------------------------------------------------- 2. temporal coverage heatmap
def fig_coverage(obs):
    _style()
    piv = (obs.assign(one=1)
           .pivot_table(index="indicator_code", columns="year", values="one",
                        aggfunc="sum", fill_value=0))
    piv = piv.reindex(sorted(piv.index), axis=0)
    fig, ax = plt.subplots(figsize=(11, 9))
    data = piv.values.astype(float)
    masked = np.ma.masked_where(data == 0, data)
    cmap = plt.colormaps["Blues"].copy()
    cmap.set_bad("#f5f5f5")  # empty cells = light gray, not dark
    im = ax.imshow(masked, aspect="auto", cmap=cmap, vmin=1, vmax=max(2, data.max()))
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, rotation=45)
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index, fontsize=9)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if data[i, j] > 0:
                ax.text(j, i, int(data[i, j]), ha="center", va="center",
                        color="white" if data[i, j] > 1 else INK, fontsize=8)
    ax.set_title("Temporal coverage — observations per indicator × year")
    ax.grid(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.5, label="# observations")
    fig.tight_layout()
    return fig, piv


# ---------------------------------------------------- 3. access trajectory + events
def fig_access_trajectory(obs, d):
    _style()
    own = _series(obs, "ACC_OWNERSHIP", "all")
    fig, ax = plt.subplots(figsize=(11, 6))
    ax.plot(own.year, own.value_numeric, "-o", color=OI["blue"], lw=2.5,
            markersize=9, zorder=5, label="Account ownership (all adults)")
    for _, r in own.iterrows():
        ax.annotate(f"{r.value_numeric:.0f}%", (r.year, r.value_numeric),
                    textcoords="offset points", xytext=(0, 11), ha="center",
                    fontsize=10, color=INK, fontweight="bold")
    # NFIS-II 70% target (2025)
    ax.axhline(70, ls="--", color=MUTED, lw=1.2)
    ax.text(2014.1, 70.8, "NFIS-II target 70% (2025)", color=MUTED, fontsize=9)

    events = d["events"].copy()
    events["date"] = pd.to_datetime(events["observation_date"])
    key = {"EVT_0001": "Telebirr launch", "EVT_0002": "Safaricom entry",
           "EVT_0003": "M-Pesa launch", "EVT_0009": "NFIS-II"}
    for eid, lbl in key.items():
        e = events[events.record_id == eid]
        if len(e):
            yr = e.iloc[0].date.year + (e.iloc[0].date.month - 1) / 12
            ax.axvline(yr, color=OI["vermillion"], ls=":", lw=1.4, alpha=0.8)
            ax.text(yr, 19.2, f" {lbl}", rotation=90, fontsize=8.5, color=OI["vermillion"],
                    ha="center", va="bottom")
    # shade the 2021-2024 slowdown
    ax.axvspan(2021, 2024, color=OI["orange"], alpha=0.08, zorder=0)
    ax.text(2022.5, 62, "+3pp\ndespite 65M+\nMM accounts", ha="center", color=OI["vermillion"],
            fontsize=9, fontweight="bold")
    ax.set_ylim(18, 78); ax.set_xlabel("Year"); ax.set_ylabel("% of adults (15+)")
    ax.set_title("Ethiopia account ownership trajectory (2014–2024) with key events")
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 4. growth rates per period
def fig_growth(obs):
    _style()
    own = _series(obs, "ACC_OWNERSHIP", "all").reset_index(drop=True)
    rows = []
    for i in range(1, len(own)):
        y0, y1 = own.year[i - 1], own.year[i]
        v0, v1 = own.value_numeric[i - 1], own.value_numeric[i]
        yrs = y1 - y0
        rows.append({"period": f"{y0}–{y1}", "pp_total": v1 - v0,
                     "pp_per_yr": (v1 - v0) / yrs})
    g = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(9, 5.5))
    colors = [OI["blue"]] * len(g)
    colors[-1] = OI["vermillion"]  # highlight the slowdown period
    bars = ax.bar(g.period, g.pp_per_yr, color=colors, zorder=3, width=0.6)
    for b, (_, r) in zip(bars, g.iterrows()):
        ax.text(b.get_x() + b.get_width() / 2, r.pp_per_yr + 0.08,
                f"+{r.pp_total:.0f}pp\n({r.pp_per_yr:.1f}/yr)", ha="center",
                color=INK, fontsize=10)
    ax.set_ylabel("Percentage points gained per year")
    ax.set_title("Account-ownership growth is decelerating\n(annualized pp gain between Findex surveys)")
    ax.grid(axis="x", visible=False); ax.margins(y=0.18)
    fig.tight_layout()
    return fig, g


# ---------------------------------------------------- 5. gender gap
def fig_gender(obs):
    _style()
    fig, ax = plt.subplots(figsize=(9, 5.5))
    years = [2021, 2024]
    male = [_series(obs, "ACC_OWNERSHIP", "male").query("year==@y").value_numeric.mean() for y in years]
    female = [_series(obs, "ACC_OWNERSHIP", "female").query("year==@y").value_numeric.mean() for y in years]
    x = np.arange(len(years)); w = 0.36
    ax.bar(x - w / 2, male, w, label="Male", color=OI["blue"], zorder=3)
    ax.bar(x + w / 2, female, w, label="Female", color=OI["orange"], zorder=3)
    for i, (m, f) in enumerate(zip(male, female)):
        ax.text(x[i] - w / 2, m + 0.6, f"{m:.0f}%", ha="center", fontsize=10, color=INK)
        ax.text(x[i] + w / 2, f + 0.6, f"{f:.0f}%", ha="center", fontsize=10, color=INK)
        ax.annotate("", (x[i] + w / 2, f), (x[i] - w / 2, m),
                    arrowprops=dict(arrowstyle="<->", color=MUTED, lw=1.2))
        ax.text(x[i], (m + f) / 2, f"  gap {m - f:.0f}pp", va="center", fontsize=9,
                color=MUTED, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(years)
    ax.set_ylabel("Account ownership (%)"); ax.set_ylim(0, 66)
    ax.set_title("Gender gap in account ownership (Findex)\nnarrowed from 20pp to 15pp, but women still lag")
    ax.legend(frameon=False, loc="upper left"); ax.grid(axis="x", visible=False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 6. Telebirr adoption + MM ownership
def fig_usage_growth(obs):
    _style()
    tb = _series(obs, "USG_TELEBIRR_USERS", "all")
    mm = _series(obs, "ACC_MM_ACCOUNT", "all")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
    # panel 1: Telebirr registered users (operator-reported)
    a1.plot(tb.year, tb.value_numeric / 1e6, "-o", color=OI["blue"], lw=2.5, markersize=9)
    for _, r in tb.iterrows():
        a1.annotate(f"{r.value_numeric/1e6:.1f}M", (r.year, r.value_numeric / 1e6),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9,
                    fontweight="bold", color=INK)
    a1.set_title("Telebirr registered users (operator)"); a1.set_ylabel("Million users")
    a1.set_xlabel("Year"); a1.margins(y=0.2)
    # panel 2: survey-reported mobile-money account ownership
    a2.plot(mm.year, mm.value_numeric, "-o", color=OI["orange"], lw=2.5, markersize=9)
    for _, r in mm.iterrows():
        a2.annotate(f"{r.value_numeric:.1f}%", (r.year, r.value_numeric),
                    textcoords="offset points", xytext=(0, 10), ha="center", fontsize=9,
                    fontweight="bold", color=INK)
    a2.set_title("Mobile-money account ownership (Findex survey)")
    a2.set_ylabel("% of adults"); a2.set_xlabel("Year"); a2.margins(y=0.2); a2.set_ylim(0, 12)
    fig.suptitle("The measurement paradox: 55M operator registrations vs ~9% survey ownership",
                 fontweight="bold", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


# ---------------------------------------------------- 7. registered vs active vs owners
def fig_registered_active(obs):
    _style()
    adults = 70e6  # approx adults 15+ (WB pop ~126M x ~55%); used only for the survey-owner bar
    tb = _series(obs, "USG_TELEBIRR_USERS", "all").value_numeric.max()
    mpesa = _series(obs, "USG_MPESA_USERS", "all").value_numeric.max()
    mpesa_act = _series(obs, "USG_MPESA_ACTIVE", "all").value_numeric.max()
    mm_own_pct = _series(obs, "ACC_MM_ACCOUNT", "all").value_numeric.max()
    survey_owners = mm_own_pct / 100 * adults
    labels = ["Telebirr\nregistered", "M-Pesa\nregistered", "M-Pesa\n90-day active",
              "Findex unique\nMM owners (est.)"]
    vals = [tb / 1e6, mpesa / 1e6, mpesa_act / 1e6, survey_owners / 1e6]
    colors = [OI["blue"], OI["sky"], OI["green"], OI["vermillion"]]
    fig, ax = plt.subplots(figsize=(10, 5.5))
    bars = ax.bar(labels, vals, color=colors, zorder=3, width=0.62)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.8, f"{v:.1f}M", ha="center",
                fontsize=10, color=INK, fontweight="bold")
    ax.set_ylabel("Accounts / users (millions)")
    ax.set_title("Registered ≠ active ≠ unique owner\nwhy 65M+ registrations translate to few new account-holders")
    ax.grid(axis="x", visible=False); ax.margins(y=0.16)
    ax.text(0.99, 0.9, "Findex owners estimated as\n9.45% × ~70M adults", transform=ax.transAxes,
            ha="right", fontsize=8.5, color=MUTED)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 8. P2P vs ATM crossover
def fig_p2p_atm(obs):
    _style()
    p2p = _series(obs, "USG_P2P_COUNT", "all")
    atm = _series(obs, "USG_ATM_COUNT", "all")
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    ax.plot(p2p.year, p2p.value_numeric / 1e6, "-o", color=OI["blue"], lw=2.5,
            markersize=9, label="P2P transactions")
    ax.plot(atm.year, atm.value_numeric / 1e6, "-s", color=OI["orange"], lw=2.5,
            markersize=9, label="ATM transactions")
    for s, c in [(p2p, OI["blue"]), (atm, OI["orange"])]:
        for _, r in s.iterrows():
            ax.annotate(f"{r.value_numeric/1e6:.0f}M", (r.year, r.value_numeric / 1e6),
                        textcoords="offset points", xytext=(0, 10), ha="center",
                        fontsize=9, color=c, fontweight="bold")
    ax.set_xticks([2024, 2025])
    ax.set_ylabel("Transactions (millions)"); ax.set_xlabel("Year")
    ax.set_title("Digital P2P overtook ATM withdrawals (crossover 2024→2025)")
    ax.legend(frameon=False, loc="upper left"); ax.grid(axis="x", visible=False)
    ax.margins(y=0.18)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 9. infrastructure / enablers
def fig_enablers(obs):
    _style()
    # indexed as % values already; grouped bar of latest value per enabler
    items = [("ACC_4G_COV", "4G coverage"), ("ACC_MOBILE_PEN", "Mobile penetration"),
             ("ACC_SMARTPHONE", "Smartphone adoption"), ("ACC_SUB_PEN", "Unique subscriber"),
             ("ENAB_ELECTRICITY", "Electricity access"), ("ACC_PHONE_OWN", "Phone ownership")]
    latest = []
    for code, name in items:
        s = _series(obs, code, "all")
        if len(s):
            latest.append((name, s.iloc[-1].value_numeric, s.iloc[-1].year))
    latest.sort(key=lambda t: t[1])
    names = [t[0] for t in latest]; vals = [t[1] for t in latest]; yrs = [t[2] for t in latest]
    fig, ax = plt.subplots(figsize=(9.5, 5.5))
    bars = ax.barh(names, vals, color=OI["green"], zorder=3)
    for b, v, y in zip(bars, vals, yrs):
        ax.text(v + 1, b.get_y() + b.get_height() / 2, f"{v:.1f}% ({y})", va="center",
                fontsize=9.5, color=INK)
    ax.set_xlabel("% (latest available year)"); ax.set_xlim(0, 100)
    ax.set_title("Digital enablers cap how far inclusion can grow\n(device & connectivity ceilings)")
    ax.grid(axis="y", visible=False); ax.margins(x=0.12)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 10. event timeline
def fig_timeline(d):
    _style()
    ev = d["events"].copy()
    ev["date"] = pd.to_datetime(ev["observation_date"])
    ev = ev.sort_values("date").reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    levels = np.tile([1, -1, 2, -2, 3, -3], int(np.ceil(len(ev) / 6)))[:len(ev)]
    for (_, r), lvl in zip(ev.iterrows(), levels):
        c = EVENT_COLORS.get(r.category, MUTED)
        ax.plot([r.date, r.date], [0, lvl], color=c, lw=1.2, zorder=2)
        ax.scatter([r.date], [lvl], s=70, color=c, zorder=3)
        ax.scatter([r.date], [0], s=22, color=c, zorder=3)
        ax.annotate(r.indicator, (r.date, lvl),
                    textcoords="offset points", xytext=(0, 8 if lvl > 0 else -14),
                    ha="center", fontsize=8, color=INK,
                    va="bottom" if lvl > 0 else "top")
    ax.axhline(0, color=INK, lw=1.2, zorder=1)
    ax.set_ylim(-3.8, 3.8); ax.get_yaxis().set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_title("Event timeline — policies, launches & milestones (2020–2025)")
    handles = [Patch(color=EVENT_COLORS[c], label=c) for c in
               sorted(ev.category.unique()) if c in EVENT_COLORS]
    ax.legend(handles=handles, ncol=4, frameon=False, loc="lower center",
              bbox_to_anchor=(0.5, -0.16), fontsize=9)
    ax.grid(False)
    fig.tight_layout()
    return fig


# ---------------------------------------------------- 11. impact-link relationship matrix
def fig_impact_matrix(d):
    _style()
    il = d["impact_links"].merge(
        d["events"][["record_id", "indicator"]].rename(columns={"record_id": "parent_id",
                                                                "indicator": "event_name"}),
        on="parent_id", how="left")
    mag = {"high": 3, "medium": 2, "low": 1, "negligible": 0.5}
    il["m"] = il.impact_magnitude.map(mag) * il.impact_direction.map(
        {"increase": 1, "decrease": -1, "stabilize": 0, "mixed": 0})
    piv = il.pivot_table(index="event_name", columns="related_indicator", values="m",
                         aggfunc="mean")
    fig, ax = plt.subplots(figsize=(12, 7))
    data = piv.values.astype(float)
    masked = np.ma.masked_invalid(data)
    im = ax.imshow(masked, aspect="auto", cmap="RdBu", vmin=-3, vmax=3)
    ax.set_xticks(range(len(piv.columns))); ax.set_xticklabels(piv.columns, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(piv.index))); ax.set_yticklabels(piv.index, fontsize=8)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            if not np.isnan(data[i, j]):
                ax.text(j, i, f"{data[i, j]:+.0f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(data[i, j]) > 1.5 else INK)
    ax.set_title("Modelled event → indicator relationships (impact_links)\nsigned magnitude: +increase / −decrease")
    fig.colorbar(im, ax=ax, shrink=0.6, label="signed magnitude")
    ax.grid(False)
    fig.tight_layout()
    return fig


def main():
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    d, obs = _load()
    figs = {
        "01_overview": fig_overview(d),
        "02_temporal_coverage": fig_coverage(obs)[0],
        "03_access_trajectory": fig_access_trajectory(obs, d),
        "04_growth_rates": fig_growth(obs)[0],
        "05_gender_gap": fig_gender(obs),
        "06_usage_growth": fig_usage_growth(obs),
        "07_registered_vs_active": fig_registered_active(obs),
        "08_p2p_vs_atm": fig_p2p_atm(obs),
        "09_enablers": fig_enablers(obs),
        "10_event_timeline": fig_timeline(d),
        "11_impact_matrix": fig_impact_matrix(d),
    }
    for name, fig in figs.items():
        out = FIG_DIR / f"{name}.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print("saved", out.relative_to(ROOT))
    plt.close("all")


if __name__ == "__main__":
    main()
