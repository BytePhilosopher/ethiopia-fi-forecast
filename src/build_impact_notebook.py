"""Assemble and execute notebooks/02_impact_model.ipynb.  Run: python src/build_impact_notebook.py"""
from pathlib import Path
import nbformat as nbf
from nbformat.v4 import new_notebook, new_markdown_cell, new_code_cell

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "notebooks" / "02_impact_model.ipynb"
md, code = new_markdown_cell, new_code_cell

cells = [
    md("# Event Impact Modeling (Task 3)\n"
       "\n"
       "**Author:** Yostina Abera  \n"
       "**Inputs:** enriched `impact_link` + `event` records · **Engine:** `src/impact_model.py`\n"
       "\n"
       "Goal: turn the `impact_link` records into a model that predicts how an indicator moves "
       "when events occur, summarise them as an **event → indicator association matrix**, and "
       "**validate** predictions against observed history. Methodology write-up: "
       "`reports/impact_model_methodology.md`."),

    code("import sys; from pathlib import Path\n"
         "sys.path.insert(0, str(Path.cwd().parent))\n"
         "import pandas as pd, numpy as np\n"
         "%matplotlib inline\n"
         "from src import impact_model as im\n"
         "pd.set_option('display.width', 200); pd.set_option('display.max_columns', 40)"),

    md("## 1. Understand the impact data\n"
       "Load impact_links and join to their parent event via `parent_id` to get event name, "
       "category and date. The result shows *which event affects which indicator, by how much, "
       "in which direction, and with what lag* — plus the unit-aware combination rule and a flag "
       "for links that are purely qualitative (no numeric estimate)."),
    code("il = im.get_impact_table()\n"
         "show = ['event_name','category','event_date','related_indicator','relationship_type',\n"
         "        'impact_direction','impact_magnitude','impact_estimate','lag_months',\n"
         "        'combine','asymptote','is_qualitative','evidence_basis','comparable_country']\n"
         "il[show].sort_values(['event_name','related_indicator'])"),

    md("## 2. Functional form — how an effect unfolds over time\n"
       "**Do effects happen immediately or build gradually?** Gradually. Each link's effect grows "
       "along a **half-life saturating ramp**\n"
       "\n"
       r"$$g(\Delta t) = 1 - 0.5^{\,\Delta t / L}, \quad \Delta t \ge 0$$"
       "\n\n"
       "where `L` = `lag_months`. So `g(L)=0.5` (the lag is the time to reach **half** the full "
       "effect), `g(2L)=0.75`, asymptoting to the full magnitude. Direct launches have small `L` "
       "(fast), enabling policies have large `L` (slow), so the lag itself encodes how gradual the "
       "effect is."),
    code("_ = im.fig_effect_curves()"),

    md("## 3. Representing & combining effects\n"
       "**How do we combine multiple events?** By indicator unit:\n"
       "- **Additive** (percentage / gap_pp indicators): effects are in *percentage points* and "
       "sum. `level(t) = anchor + Σ Mᵢ·[g(t) − g(anchor)]`\n"
       "- **Multiplicative** (count / currency indicators): effects are *percent changes* and "
       "compound. `level(t) = anchor · Π (1 + (Mᵢ/100)·[g(t) − g(anchor)])`\n"
       "\n"
       "Effects are measured as an **increment relative to the anchor date**, so an event that "
       "began before the anchor is not double-counted. Purely qualitative 'enabling' links (no "
       "numeric estimate, e.g. the 2020 directive) enter the *matrix* but are **excluded from the "
       "arithmetic** — assigning them a band-midpoint number would be fabrication."),

    md("## 4. Event → indicator association matrix\n"
       "The deliverable: rows = events, columns = key indicators, values = **estimated effect** "
       "(pp for percentages, % for counts). Colour encodes the unit-free signed magnitude band so "
       "cells are comparable across differing units; `*` marks qualitative (band-derived) cells."),
    code("num, ordv = im.build_association_matrix(il)\n"
         "num.round(0)"),
    code("_ = im.fig_association_matrix(il)"),

    md("## 5. Comparable-country evidence\n"
       "Where Ethiopian pre/post data is thin, magnitudes are borrowed from documented impacts in "
       "similar markets and flagged via `evidence_basis` = `literature` and `comparable_country`. "
       "These are the estimates most in need of validation (Section 6)."),
    code("il[il.evidence_basis=='literature'][['event_name','related_indicator',\n"
         "     'impact_estimate','lag_months','comparable_country']].sort_values('comparable_country')"),

    md("## 6. Test the model against historical data\n"
       "We have two indicators with enough history to check: **ACC_MM_ACCOUNT** and "
       "**ACC_OWNERSHIP**. Anchor at the 2021 observation and predict 2024 from the events active "
       "in between."),
    code("import json\n"
         "res = im.validate(il)\n"
         "print(json.dumps(res, indent=2, default=str))"),
    code("_ = im.fig_validation(il)"),

    md("### What the validation shows\n"
       "- **ACC_MM_ACCOUNT — well calibrated.** Predicted **8.9%** vs observed **9.45%** (anchor "
       "4.7% in 2021). The M-Pesa `+5pp` estimate reproduces the observed rise almost exactly; no "
       "attenuation needed.\n"
       "- **ACC_OWNERSHIP — naive model over-predicts badly.** Predicted **62.7%** vs observed "
       "**49%**. The account-ownership impacts (Telebirr `+15pp` ex-Kenya, Fayda `+10pp` ex-India, "
       "NFIS-II `+8pp`) assume mobile money *creates new account-holders*. In Ethiopia it did not: "
       "mobile-money-only users are ~0.5% and bank accounts are already accessible, so registrations "
       "mostly digitised the **already-banked** (the EDA paradox). Matching the observed +3pp "
       "requires an attenuation of **α ≈ 0.18** — the borrowed impacts realise only ~18% of their "
       "nominal effect on *ownership* here."),

    md("## 7. Refine the estimates\n"
       "Adjustments, with reasoning and a confident-vs-uncertain tag:"),
    code("refine = pd.DataFrame([\n"
         " {'indicator':'ACC_OWNERSHIP','change':'apply α≈0.18 to imported ownership impacts',\n"
         "  'reason':'mobile money digitised existing account-holders, not new ones (registered≠owner)',\n"
         "  'confidence':'medium — one calibration point (2021→2024)'},\n"
         " {'indicator':'ACC_MM_ACCOUNT','change':'keep M-Pesa +5pp as-is',\n"
         "  'reason':'predicted 8.9% vs observed 9.45% — already accurate',\n"
         "  'confidence':'high'},\n"
         " {'indicator':'ACC_MM_ACCOUNT','change':'add a Telebirr→ACC_MM_ACCOUNT link (future work)',\n"
         "  'reason':'most 2021→2023 MM-account growth predates M-Pesa (Aug-2023) and is Telebirr-driven; '\n"
         "           'current fit is right at the endpoint but mis-attributes the driver',\n"
         "  'confidence':'medium'},\n"
         " {'indicator':'USG_TELEBIRR_USERS / USG_MPESA_USERS','change':'model as adoption curves, not % shocks',\n"
         "  'reason':'these series are created from zero by the launch; a %-change baseline is undefined',\n"
         "  'confidence':'high (structural)'},\n"
         " {'indicator':'AFF_DATA_INCOME','change':'treat as mixed/uncertain sign',\n"
         "  'reason':'competition lowers cost while FX liberalisation raised it — net effect ambiguous',\n"
         "  'confidence':'low'},\n"
         "])\n"
         "refine"),

    md("## 8. Confidence summary\n"
       "**Confident:** the *direction* of every link; the ACC_MM_ACCOUNT magnitude; the functional "
       "form (gradual build); the finding that ownership impacts are over-stated for Ethiopia.  \n"
       "**Uncertain:** the exact α (single calibration point); count-series magnitudes lacking "
       "estimates; long-lag policy effects (NFIS-II, foreign banks) not yet observable; "
       "affordability sign.\n"
       "\n"
       "These calibrated, unit-aware effects and the half-life ramp feed directly into the "
       "forecasting phase (Task 4), where Access and Usage are projected as separate targets with "
       "event intervention terms and explicit uncertainty bounds."),
]

nb = new_notebook(cells=cells, metadata={
    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
    "language_info": {"name": "python"}})
OUT.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, OUT)
print("wrote", OUT.relative_to(ROOT), f"({len(cells)} cells)")
