"""Ethiopia Financial Inclusion — interactive dashboard (Task 5).

Run:  streamlit run dashboard/app.py

Pages: Overview · Trends · Forecasts · Inclusion Projections.
Reuses the analysis engines in src/ (load_data, impact_model, forecast) and the
dashboard/data_access.py helpers. Charts use Plotly (interactive) with the same
Okabe-Ito colorblind-safe palette as the notebooks.
"""
from pathlib import Path
import sys

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard import data_access as da          # noqa: E402
from src import forecast as fc                    # noqa: E402
from src import impact_model as im                # noqa: E402

st.set_page_config(page_title="Ethiopia Financial Inclusion", page_icon="📊", layout="wide")
OI = da.OI


# --------------------------------------------------------------------- data (cached)
@st.cache_data
def _obs():
    return da.load_observations()


@st.cache_data
def _forecast_table():
    return fc.forecast_table()


@st.cache_data
def _unified():
    from src.load_data import load_all
    return load_all(processed=True)["unified"]


@st.cache_data
def _assoc_matrix():
    num, ordv = im.build_association_matrix()
    return num, ordv


def _style(fig, height=430, ytitle="", xtitle=""):
    fig.update_layout(
        template="plotly_white", height=height, margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        yaxis_title=ytitle, xaxis_title=xtitle, font=dict(size=13),
    )
    fig.update_xaxes(gridcolor=da.GRID); fig.update_yaxes(gridcolor=da.GRID)
    return fig


# =============================================================== OVERVIEW
def page_overview(obs):
    st.header("Overview")
    st.caption("Current state of financial inclusion in Ethiopia — headline indicators, the "
               "P2P/ATM crossover, and how account-ownership growth has decelerated.")

    cards = da.key_metrics(obs)
    cols = st.columns(len(cards))
    for c, m in zip(cols, cards):
        c.metric(f"{m['label']} ({m['year']})", m["value"], m["delta"])

    st.divider()
    left, right = st.columns([1, 1.4])

    with left:
        st.subheader("P2P / ATM crossover")
        ratio, yr = da.crossover_ratio(obs)
        if ratio is not None:
            st.metric(f"Crossover ratio ({yr})", f"{ratio:.2f}",
                      "digital P2P exceeds ATM" if ratio > 1 else "ATM still leads")
            fig = go.Figure(go.Indicator(
                mode="gauge+number", value=ratio,
                gauge={"axis": {"range": [0, 2]},
                       "bar": {"color": OI["blue"]},
                       "threshold": {"line": {"color": OI["vermillion"], "width": 3},
                                     "thickness": 0.8, "value": 1.0}},
                number={"suffix": " ×"}))
            fig.update_layout(height=260, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, width='stretch')
            st.caption("A ratio above 1.0 means more digital P2P transactions than ATM "
                       "withdrawals — a behavioural shift toward digital rails.")

    with right:
        st.subheader("Account-ownership growth is decelerating")
        g = da.growth_rates(obs)
        colors = [OI["blue"]] * len(g)
        if len(colors):
            colors[-1] = OI["vermillion"]
        fig = go.Figure(go.Bar(x=g["period"], y=g["pp_per_year"], marker_color=colors,
                               text=[f"+{v:.0f}pp<br>({r:.1f}/yr)" for v, r in
                                     zip(g["pp_total"], g["pp_per_year"])],
                               textposition="outside"))
        _style(fig, height=340, ytitle="pp gained per year")
        st.plotly_chart(fig, width='stretch')
        st.caption("Annualized percentage-point gain between Findex surveys. The most recent "
                   "period (highlighted) is the slowest despite the mobile-money boom.")


# =============================================================== TRENDS
def page_trends(obs):
    st.header("Trends")
    st.caption("Explore indicator time series. Pick indicators, set a year range, and compare "
               "channels.")

    codes = [c for c in da.INDICATOR_LABELS if not obs[obs.indicator_code == c].empty]
    default = ["ACC_OWNERSHIP", "ACC_MM_ACCOUNT", "USG_DIGITAL_PAY"]
    picked = st.multiselect("Indicators", codes, default=[c for c in default if c in codes],
                            format_func=lambda c: da.INDICATOR_LABELS.get(c, c))
    yr_min, yr_max = int(obs.year.min()), int(obs.year.max())
    lo, hi = st.slider("Year range", yr_min, yr_max, (yr_min, yr_max))

    # chart 1: percentage-type indicators (shared % axis — no dual axis)
    pct = ["ACC_OWNERSHIP", "ACC_MM_ACCOUNT", "USG_DIGITAL_PAY", "ACC_4G_COV",
           "ACC_PHONE_OWN", "ACC_SMARTPHONE", "GEN_GAP_ACC"]
    fig = go.Figure()
    palette = list(OI.values())
    for i, code in enumerate([c for c in picked if c in pct]):
        s = da.get_series(obs, code)
        s = s[(s.year >= lo) & (s.year <= hi)]
        fig.add_trace(go.Scatter(x=s["date"], y=s["value"], mode="lines+markers",
                                 name=da.INDICATOR_LABELS.get(code, code),
                                 line=dict(color=palette[i % len(palette)], width=3)))
    _style(fig, ytitle="% of adults", xtitle="Year")
    st.plotly_chart(fig, width='stretch')
    if any(c not in pct for c in picked):
        st.info("Count-based indicators (users, transactions) are shown in the channel "
                "comparison below to avoid mixing scales on one axis.")

    st.divider()
    st.subheader("Channel comparison")
    tab1, tab2 = st.tabs(["P2P vs ATM transactions", "Telebirr vs M-Pesa users"])
    with tab1:
        fig = go.Figure()
        for code, col in [("USG_P2P_COUNT", OI["blue"]), ("USG_ATM_COUNT", OI["orange"])]:
            s = da.get_series(obs, code)
            fig.add_trace(go.Scatter(x=s["date"], y=s["value"] / 1e6, mode="lines+markers",
                                     name=da.INDICATOR_LABELS[code], line=dict(color=col, width=3)))
        _style(fig, ytitle="Transactions (millions)", xtitle="Year")
        st.plotly_chart(fig, width='stretch')
    with tab2:
        fig = go.Figure()
        for code, col in [("USG_TELEBIRR_USERS", OI["blue"]), ("USG_MPESA_USERS", OI["green"])]:
            s = da.get_series(obs, code)
            fig.add_trace(go.Bar(x=s["year"], y=s["value"] / 1e6,
                                 name=da.INDICATOR_LABELS[code], marker_color=col))
        _style(fig, ytitle="Users (millions)", xtitle="Year")
        fig.update_layout(barmode="group")
        st.plotly_chart(fig, width='stretch')

    with st.expander("⬇ Download the underlying data"):
        st.download_button("Download enriched dataset (CSV)",
                           da.download_bytes(_unified()),
                           "ethiopia_fi_unified_data_enriched.csv", "text/csv")


# =============================================================== FORECASTS
def page_forecasts(obs):
    st.header("Forecasts (2025–2027)")
    st.caption("Account ownership and digital-payment usage projections with confidence intervals "
               "and scenarios. Choose which model to display.")

    model = st.radio("Model", ["Event-augmented scenarios", "Linear trend + 95% PI", "Both"],
                     horizontal=True)
    show_scen = model in ("Event-augmented scenarios", "Both")
    show_lin = model in ("Linear trend + 95% PI", "Both")

    own = fc.ownership_series()
    scen = fc.ownership_scenarios()
    lin, params = fc.linear_trend(own)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=own["year"], y=own["value"], mode="lines+markers",
                             name="observed (Findex)", line=dict(color=da.INK, width=3)))
    if show_lin:
        fig.add_trace(go.Scatter(x=lin["year"], y=lin["hi"], mode="lines",
                                 line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=lin["year"], y=lin["lo"], mode="lines", fill="tonexty",
                                 fillcolor="rgba(107,107,107,0.15)", line=dict(width=0),
                                 name="linear 95% PI"))
        fig.add_trace(go.Scatter(x=lin["year"], y=lin["value"], mode="lines",
                                 name="linear trend", line=dict(color=da.MUTED, dash="dash")))
    if show_scen:
        colz = {"optimistic": OI["green"], "base": OI["blue"], "pessimistic": OI["vermillion"]}
        x0, y0 = own["year"].iloc[-1], own["value"].iloc[-1]
        for name, col in colz.items():
            fig.add_trace(go.Scatter(x=[x0] + list(scen.index), y=[y0] + list(scen[name]),
                                     mode="lines+markers", name=name, line=dict(color=col, width=3)))
    fig.add_hline(y=70, line_dash="dot", line_color=OI["orange"],
                  annotation_text="NFIS-II 70% target", annotation_position="top left")
    _style(fig, height=470, ytitle="Account ownership (% adults)", xtitle="Year")
    st.plotly_chart(fig, width='stretch')

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Digital-payment usage")
        dp = fc.digital_pay_scenarios()
        fig = go.Figure()
        colz = {"optimistic": OI["green"], "base": OI["blue"], "pessimistic": OI["vermillion"]}
        for name, col in colz.items():
            fig.add_trace(go.Scatter(x=[2024] + list(dp.index), y=[fc.DP_ANCHOR] + list(dp[name]),
                                     mode="lines+markers", name=name, line=dict(color=col, width=3)))
        _style(fig, ytitle="% of adults", xtitle="Year")
        st.plotly_chart(fig, width='stretch')
        st.caption("Anchored on a single Findex point → widest uncertainty (see interpretation).")
    with c2:
        st.subheader("Key projected milestones")
        t = _forecast_table()
        own_row = t[(t.target == "ACC_OWNERSHIP") & (t.year == 2027)].iloc[0]
        dp_row = t[(t.target == "USG_DIGITAL_PAY") & (t.year == 2027)].iloc[0]
        st.markdown(
            f"- **Account ownership 2027 (base):** {own_row['base']}% "
            f"(range {own_row['pessimistic']}–{own_row['optimistic']}%)\n"
            f"- **Digital-payment usage 2027 (base):** {dp_row['base']}% "
            f"(range {dp_row['pessimistic']}–{dp_row['optimistic']}%)\n"
            f"- **Linear-trend slope:** {params['slope']:.1f} pp/yr (ignores deceleration)\n"
            f"- **NFIS-II 70% target:** not reachable by 2027 on any scenario\n"
            f"- **Consortium 60% target:** reached only in the optimistic path, ~2027+")

    st.subheader("Event → indicator association matrix")
    num, ordv = _assoc_matrix()
    z = ordv.reindex(sorted(ordv.index))
    heat = go.Figure(go.Heatmap(z=z.values, x=list(z.columns), y=list(z.index),
                                colorscale="RdBu", zmid=0, zmin=-3, zmax=3,
                                colorbar=dict(title="signed band")))
    heat.update_layout(template="plotly_white", height=460, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(heat, width='stretch')
    st.caption("From the impact model (Task 3): which events push which indicators, and how "
               "strongly. Colour = signed magnitude band.")

    with st.expander("⬇ Download forecasts"):
        st.download_button("Download forecast table (CSV)", da.download_bytes(_forecast_table()),
                           "forecasts_2025_2027.csv", "text/csv")


# =============================================================== INCLUSION PROJECTIONS
def page_projections(obs):
    st.header("Inclusion Projections")
    st.caption("Financial-inclusion rate (account ownership) projections and progress toward the "
               "consortium's 60% target.")

    scenario = st.radio("Scenario", ["optimistic", "base", "pessimistic"], index=1, horizontal=True)
    scen = fc.ownership_scenarios()
    own = fc.ownership_series()
    proj_2027 = scen[scenario].iloc[-1]
    current = own["value"].iloc[-1]
    target = da.CONSORTIUM_TARGET

    c1, c2 = st.columns([1.2, 1])
    with c1:
        colz = {"optimistic": OI["green"], "base": OI["blue"], "pessimistic": OI["vermillion"]}
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=own["year"], y=own["value"], mode="lines+markers",
                                 name="observed", line=dict(color=da.INK, width=3)))
        fig.add_trace(go.Scatter(x=[own["year"].iloc[-1]] + list(scen.index),
                                 y=[current] + list(scen[scenario]), mode="lines+markers",
                                 name=f"{scenario} projection", line=dict(color=colz[scenario], width=3)))
        fig.add_hline(y=target, line_dash="dot", line_color=OI["orange"],
                      annotation_text=f"{target:.0f}% consortium target")
        _style(fig, height=430, ytitle="Account ownership (% adults)", xtitle="Year")
        st.plotly_chart(fig, width='stretch')
    with c2:
        st.subheader("Progress toward 60%")
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta", value=proj_2027,
            delta={"reference": target, "suffix": " pp vs target"},
            gauge={"axis": {"range": [0, 100]},
                   "bar": {"color": colz[scenario]},
                   "steps": [{"range": [0, target], "color": "#f2f2f2"}],
                   "threshold": {"line": {"color": OI["orange"], "width": 4},
                                 "thickness": 0.85, "value": target}},
            title={"text": f"Projected 2027 ({scenario})"}))
        fig.update_layout(height=300, margin=dict(l=20, r=20, t=60, b=10))
        st.plotly_chart(fig, width='stretch')
        gap = proj_2027 - target
        st.metric("2027 vs 60% target", f"{proj_2027:.1f}%", f"{gap:+.1f} pp")

    st.divider()
    st.subheader("Answers to the consortium's key questions")
    with st.expander("Why did account ownership stagnate (+3pp) despite 65M+ mobile-money accounts?"):
        st.markdown(
            "Mobile-money-*only* users are ~0.5% and bank accounts are already easily accessible, "
            "so Telebirr/M-Pesa registrations mostly went to people who **already had an account**. "
            "Findex counts *any* account, so the registrations added a payment channel, not new "
            "account-holders. Our impact model quantifies this: imported ownership effects realise "
            "only ~18% of their nominal size here (α≈0.18).")
    with st.expander("Will Ethiopia meet its inclusion targets?"):
        st.markdown(
            f"**No, not the NFIS-II 70% (2025) target** — that needs +21pp in a year vs ~+1pp/yr "
            f"observed. The **60% consortium target** is reached only on the optimistic path, and "
            f"not before ~2027. Base case: **~54% by 2027**.")
    with st.expander("What is the gender gap and how is it evolving?"):
        st.markdown(
            "The account-ownership gap narrowed from ~20pp (2021) to ~15pp (2024) — men 57% vs "
            "women 42% — but it tracks a **17pp phone-ownership gap** (men 50% vs women 33%). "
            "Closing the account gap depends on closing the device gap.")
    with st.expander("What drives inclusion, and where should investment focus?"):
        st.markdown(
            "Usage is driven by product launches and **interoperability** (EthioPay, "
            "M-Pesa–EthSwitch); access is enabled slowly by **digital ID (Fayda)** and policy. But "
            "the binding constraint is **demand-side device access** (phone 41%, smartphone 40%). "
            "The highest-leverage investment is closing the phone/smartphone gap, especially for women.")


# =============================================================== MAIN
def main():
    st.sidebar.title("📊 Ethiopia FI")
    st.sidebar.caption("Financial-inclusion data, event impacts & forecasts")
    page = st.sidebar.radio("Navigate", ["Overview", "Trends", "Forecasts", "Inclusion Projections"])
    st.sidebar.divider()
    st.sidebar.caption("Data: enriched unified dataset (87 records). Engines: src/impact_model.py, "
                       "src/forecast.py. Palette is colorblind-safe.")
    obs = _obs()

    st.title("Ethiopia Financial Inclusion Dashboard")
    {"Overview": page_overview, "Trends": page_trends, "Forecasts": page_forecasts,
     "Inclusion Projections": page_projections}[page](obs)


if __name__ == "__main__":
    main()
