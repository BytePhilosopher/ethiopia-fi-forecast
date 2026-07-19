"""Assemble and execute notebooks/01_eda.ipynb from cell definitions.

Keeping the notebook as generated code means the narrative, the inline tables and
the figures never drift from src/eda.py. Run:  python src/build_notebook.py
"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "01_eda.ipynb"

md = new_markdown_cell
code = new_code_cell

cells = [
    md("# Ethiopia Financial Inclusion — Exploratory Data Analysis (Task 2)\n"
       "\n"
       "**Author:** Yostina Abera  \n"
       "**Dataset:** `data/processed/ethiopia_fi_unified_data_enriched.csv` (87 records)\n"
       "\n"
       "This notebook explores the unified dataset to understand what drives financial "
       "inclusion in Ethiopia, why headline account ownership stagnated at **+3pp (2021→2024)** "
       "despite 65M+ mobile-money registrations, and which data gaps most limit forecasting.\n"
       "\n"
       "Figures are rendered by tested functions in `src/eda.py` (Okabe-Ito colorblind-safe "
       "palette, no dual-axis charts) and also saved to `reports/figures/`. "
       "Interpretation is grounded in **Sheet D (Market Nuances)** of the enrichment guide: "
       "P2P is used for commerce (not just transfers), mobile-money-*only* users are ~0.5%, "
       "bank accounts are easily accessible, and credit penetration is very low."),

    code("import sys\n"
         "from pathlib import Path\n"
         "sys.path.insert(0, str(Path.cwd().parent))  # repo root on path\n"
         "import pandas as pd\n"
         "import matplotlib.pyplot as plt\n"
         "%matplotlib inline\n"
         "from src import eda\n"
         "from src.load_data import load_all\n"
         "\n"
         "d, obs = eda._load()\n"
         "pd.set_option('display.max_rows', 120)\n"
         "print('Loaded', len(d['unified']), 'records;', obs.indicator_code.nunique(), 'indicators')"),

    md("## 1. Dataset overview\n"
       "Composition by `record_type`, `pillar` and `source_type`, plus the confidence mix."),
    code("u = d['unified']\n"
         "overview = {\n"
         "    'by record_type': u.record_type.value_counts(),\n"
         "    'by pillar (obs/target/impact)': u[u.pillar.notna()].pillar.value_counts(),\n"
         "    'by source_type': u.source_type.value_counts(),\n"
         "    'by confidence': u.confidence.value_counts(),\n"
         "}\n"
         "for k, v in overview.items():\n"
         "    print(f'\\n=== {k} ==='); print(v.to_string())"),
    code("_ = eda.fig_overview(d)"),

    md("## 2. Temporal coverage & data gaps\n"
       "Which indicator has data in which year? The heatmap makes the **sparsity** obvious: "
       "only account ownership and Telebirr users form multi-point time series; most indicators "
       "are single snapshots."),
    code("fig, piv = eda.fig_coverage(obs)  # inline auto-displays the open figure"),
    code("# Sparsity summary: distinct years of coverage per indicator\n"
         "cov = (obs.groupby('indicator_code')\n"
         "          .agg(n_obs=('value_numeric','size'),\n"
         "               years=('year', lambda s: sorted(s.unique().tolist())))\n"
         "          .assign(n_years=lambda x: x['years'].map(len))\n"
         "          .sort_values(['n_years','n_obs'], ascending=False))\n"
         "single = cov[cov.n_years == 1]\n"
         "print(f'{len(cov)} indicators total; {len(single)} have data in only ONE year '\n"
         "      f'({len(single)/len(cov):.0%}). Only {(cov.n_years>=2).sum()} span >=2 years.')\n"
         "print('\\nMulti-year series (usable for trend estimation):')\n"
         "print(cov[cov.n_years >= 2][['n_obs','years']].to_string())"),

    md("## 3. Data-quality assessment\n"
       "Confidence is high for official/operator figures and medium for secondary sources. "
       "One systematic correction was applied upstream in `build_processed_dataset.py`: the "
       "starter main-sheet documentation columns were shifted one position left "
       "(`comparable_country` held the collector name, `collected_by` held a date, etc.); the "
       "processed data restores the intended alignment. See "
       "`reports/data_quality_assessment.md` for the full limitations register."),
    code("qual = (u.assign(one=1)\n"
         "         .pivot_table(index='pillar', columns='confidence', values='one',\n"
         "                      aggfunc='sum', fill_value=0))\n"
         "print('Confidence by pillar:'); print(qual.to_string())\n"
         "print('\\nShare high-confidence:', f\"{(u.confidence=='high').mean():.0%}\")"),

    md("## 4. Access analysis — the account-ownership story\n"
       "### 4.1 Trajectory (2014–2024) with events overlaid"),
    code("_ = eda.fig_access_trajectory(obs, d)"),
    md("### 4.2 Growth is decelerating\n"
       "Annualized gain fell from **+4.3pp/yr (2014–17)** to **+1.0pp/yr (2021–24)** — the "
       "period of the biggest mobile-money push."),
    code("fig, g = eda.fig_growth(obs)\n"
         "print(g.to_string(index=False))"),
    md("### 4.3 Gender gap\n"
       "The gap narrowed from ~20pp to ~15pp, but women's ownership (42%) still trails men's (57%). "
       "A key mechanism is device access: only 33% of women own a phone vs 50% of men."),
    code("_ = eda.fig_gender(obs)"),
    md("### 4.4 Why the 2021–2024 slowdown?\n"
       "Account ownership rose only **46%→49%** while Telebirr alone registered ~55M accounts. "
       "The Market-Nuance explanation: Ethiopia's bank accounts are already easily accessible, "
       "and mobile-money-*only* users are ~0.5%, so most Telebirr/M-Pesa sign-ups went to people "
       "who **already had an account** — adding a payment channel, not a new account-holder. "
       "Findex counts *any* account, so those registrations barely move the headline. The "
       "binding constraints are now demand-side: phone ownership (41%), smartphone adoption (40%) "
       "and financial literacy — not the supply of accounts."),

    md("## 5. Usage (digital payments) analysis\n"
       "### 5.1 The measurement paradox: operator registrations vs survey ownership"),
    code("_ = eda.fig_usage_growth(obs)"),
    md("### 5.2 Registered ≠ active ≠ unique owner\n"
       "Operator registration counts massively overstate unique inclusion."),
    code("eda.fig_registered_active(obs)\n"
         "# quantify the gaps\n"
         "tb = eda._series(obs,'USG_TELEBIRR_USERS').value_numeric.max()\n"
         "mp = eda._series(obs,'USG_MPESA_USERS').value_numeric.max()\n"
         "mp_act = eda._series(obs,'USG_MPESA_ACTIVE').value_numeric.max()\n"
         "print(f'Total registered (Telebirr+M-Pesa): {(tb+mp)/1e6:.1f}M')\n"
         "print(f'M-Pesa active rate: {mp_act/mp:.0%} (7.1M of 10.8M)')\n"
         "print('Findex mobile-money account ownership: 9.45% of adults (~6.6M)')"),
    md("### 5.3 P2P has overtaken ATM withdrawals\n"
       "Digital P2P (used for commerce, per Nuance D) crossed above ATM transaction counts — a "
       "genuine behavioural shift toward digital rails even as *account* growth stalled."),
    code("_ = eda.fig_p2p_atm(obs)"),

    md("## 6. Infrastructure & enablers\n"
       "Device and connectivity ceilings bound how far Access/Usage can realistically grow. "
       "4G coverage nearly doubled (37.5%→70.8%), but phone ownership (41%) and smartphone "
       "adoption (40%) are the true near-term ceilings — **candidate leading indicators** for "
       "the next Findex round."),
    code("_ = eda.fig_enablers(obs)"),

    md("## 7. Event timeline\n"
       "All cataloged events (policies, launches, milestones), colored by category."),
    code("_ = eda.fig_timeline(d)"),

    md("## 8. Relationships & correlation\n"
       "**Direct time-series correlation is not feasible here:** the multi-point indicators "
       "(account ownership, Telebirr users) barely share observation years, so pairwise "
       "correlation would be spurious (n≈1 overlap). Instead we read relationships from the "
       "`impact_link` records, which encode expected event→indicator effects and their evidence "
       "basis. Note: for `AFF_DATA_INCOME` (data cost as % of GNI) an *increase* means **less** "
       "affordable."),
    code("eda.fig_impact_matrix(d)\n"
         "# What do impact_links emphasise?\n"
         "il = d['impact_links']\n"
         "print('Impact links by affected pillar:'); print(il.pillar.value_counts().to_string())\n"
         "print('\\nBy evidence basis:'); print(il.evidence_basis.value_counts().to_string())"),

    md("## 9. Key insights (summary)\n"
       "Full write-up with evidence in **`reports/eda_key_insights.md`**.\n"
       "\n"
       "1. **Access has plateaued** — ownership grew only +3pp (2021→2024), decelerating to "
       "~1pp/yr, despite 65M+ mobile-money registrations.\n"
       "2. **The paradox is a measurement + market-structure artifact** — mobile-money-only "
       "users are ~0.5%; registrations went to the already-banked, so *any-account* ownership "
       "barely moved.\n"
       "3. **Registered ≠ active ≠ owner** — 65M registered vs ~6.6M Findex unique owners; "
       "M-Pesa 90-day active rate is 66%; agents average <1 transaction/day.\n"
       "4. **Usage is shifting digital even though access stalled** — P2P overtook ATM "
       "withdrawals; the frontier is now *usage depth*, not account supply.\n"
       "5. **The gender gap is device-driven** — 15pp account gap tracks a 17pp phone-ownership "
       "gap (women 33% vs men 50%).\n"
       "6. **Binding constraints are demand-side enablers** — phone (41%) & smartphone (40%) "
       "ownership are the ceilings and the best leading indicators for the next Findex.\n"
       "\n"
       "**Hypotheses for the impact-modeling phase:**\n"
       "- Telebirr/M-Pesa registrations predict *usage* (P2P volume) far better than *ownership*.\n"
       "- Phone/smartphone ownership is a stronger leading indicator of Findex ownership than "
       "4G coverage.\n"
       "- NFIS-II and the 2020 payments directive act as *enabling* (slow, structural) drivers, "
       "not step-changes."),
]

nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"},
})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print("wrote", OUT.relative_to(ROOT), f"({len(cells)} cells)")
