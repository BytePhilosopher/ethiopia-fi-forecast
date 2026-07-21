# Event Impact Modeling — Methodology (Task 3)

**Author:** Yostina Abera
**Engine:** [`src/impact_model.py`](../src/impact_model.py) · **Notebook:** [`notebooks/02_impact_model.ipynb`](../notebooks/02_impact_model.ipynb)
**Matrix:** [`reports/figures/13_association_matrix.png`](figures/13_association_matrix.png) · **Validation:** [`figures/14_validation.png`](figures/14_validation.png)

This documents how event impacts were modeled, the sources for every estimate, the validation
results, and the assumptions and uncertainties.

---

## 1. Objective and inputs
Translate the 21 `impact_link` records into a model that predicts how an indicator moves when
events occur. Each link, joined to its parent event via `parent_id`, supplies: the **event**
(name, category, date), the **affected indicator**, the **direction** (increase/decrease), a
qualitative **magnitude** band, an optional numeric **impact_estimate**, a **lag** (months), and
an **evidence basis** (empirical / literature / theoretical) with an optional **comparable
country**.

## 2. Functional form — effect over time
**Effects build gradually, not instantly.** The fraction of a link's full effect realized `Δt`
months after the event follows a **half-life saturating ramp**:

$$g(\Delta t) = 1 - 0.5^{\,\Delta t / L}, \qquad \Delta t \ge 0 \ \ (\text{else } 0)$$

where `L = lag_months`. Properties: `g(L)=0.50`, `g(2L)=0.75`, `g(3L)=0.875`, asymptoting to the
full magnitude. The lag is therefore interpreted as **"months to half of the full effect,"** and
it alone controls how gradual the response is — direct product launches carry small `L` (3–6 mo),
enabling policies carry large `L` (15–36 mo).

**Why this form.** It is smooth, monotone, needs a single parameter already present in the data
(`lag`), starts at the event with zero effect, and never overshoots. Alternatives considered and
rejected for this dataset:
- *Immediate step* (`effect = M` at the event): ignores diffusion; implausible for adoption.
- *Linear ramp to a cutoff*: requires a second parameter (end date) we don't have.
- *Logistic/S-curve centred at `L`*: adds a width parameter with no data to fit it; the half-life
  ramp is the parsimonious choice.

## 3. Combining effects, and units
Indicators are classified by `value_type`:

| Class | value_type | Estimate unit | Combination |
|-------|-----------|---------------|-------------|
| **Additive** | `percentage`, `gap_pp` | percentage **points** | `level(t) = anchor + Σᵢ Mᵢ·[g(t) − g(t_anchor)]` |
| **Multiplicative** | `count`, `currency_*`, `ratio` | **percent** change | `level(t) = anchor · Πᵢ (1 + (Mᵢ/100)·[g(t) − g(t_anchor)])` |

Effects are measured as an **increment relative to the anchor date**, `g(t) − g(t_anchor)`, so
events already partly realized at the anchor are not double-counted. The implicit **counterfactual**
is "no further change absent cataloged events."

**Qualitative links are excluded from the arithmetic.** Three links (Telebirr→users,
M-Pesa→users, the 2020 directive→MM-accounts/users) have no numeric estimate. Rather than invent a
band-midpoint number, they are shown in the association matrix (flagged `*`) but do **not** enter
the level simulation. Two of them are "creation" links — they bring a count series into existence
from zero, where a percent-change baseline is undefined; those belong in the Task-4 adoption-curve
model, not here.

## 4. The association matrix
Rows = events, columns = key indicators, values = **estimated effect** (pp for percentages, % for
counts). In the heatmap, **colour** encodes the unit-free signed magnitude band (−3…+3) so cells
are comparable despite mixed units, and **text** shows the native-unit estimate (`*` = qualitative).
This is the compact answer to "which events affect which indicators, and by how much."

## 5. Sources for all impact estimates
Every magnitude traces to `evidence_basis` + `comparable_country` on the link:

| Basis | Meaning | Links (examples) |
|-------|---------|------------------|
| `empirical` | observed Ethiopian data | Telebirr→P2P (+25%), Safaricom→4G (+15pp), FX→data-cost (+30%) |
| `literature` | documented effect in a comparable country | Telebirr→ownership (+15pp, **Kenya**), Fayda→ownership (+10pp, **India**), M-Pesa EthSwitch→active (+15%, **Tanzania**), Foreign banks→borrowing (+8pp, **Kenya**) |
| `theoretical` | economic reasoning, no direct figure | M-Pesa→MM-account (+5pp), NFIS-II→ownership (+8pp), NDPS→digital-pay (+10%) |

Comparable-country transfers are the estimates most exposed to bias — which the validation targets.

## 6. Validation results (predicted vs observed)
Anchor at the 2021 Findex observation; predict 2024 from intervening events.

| Indicator | Anchor (2021) | Observed 2024 | Predicted (naive) | Verdict |
|-----------|:-------------:|:-------------:|:-----------------:|---------|
| **ACC_MM_ACCOUNT** | 4.7% | **9.45%** | **8.9%** | ✅ well calibrated — M-Pesa `+5pp` reproduces the rise |
| **ACC_OWNERSHIP** | 46% | **49%** | **62.7%** | ❌ over-predicts by ~14pp → needs attenuation **α ≈ 0.18** |

**Interpretation of the ownership miss.** The imported ownership impacts (Telebirr +15pp, Fayda
+10pp, NFIS-II +8pp) assume mobile money *creates new account-holders*. In Ethiopia it did not:
mobile-money-only users are ~0.5% and bank accounts are already easily accessible, so registrations
mostly digitised the **already-banked** (the EDA "+3pp paradox"). Matching the observed +3pp implies
the borrowed effects realise only **~18%** of their nominal magnitude on *ownership* here.

## 7. Refinements (with reasoning and confidence)
| Indicator | Adjustment | Reasoning | Confidence |
|-----------|-----------|-----------|-----------|
| ACC_OWNERSHIP | apply **α ≈ 0.18** to imported ownership impacts | registered ≠ owner; MM digitised existing customers | medium (one calibration point) |
| ACC_MM_ACCOUNT | keep M-Pesa **+5pp** unchanged | predicted 8.9% vs observed 9.45% — already accurate | high |
| ACC_MM_ACCOUNT | *(future)* add a **Telebirr→ACC_MM_ACCOUNT** link | most 2021→2023 MM-account growth predates M-Pesa (Aug-2023) and is Telebirr-driven; the endpoint fit is right but the driver is mis-attributed | medium |
| Telebirr/M-Pesa users | model as **adoption curves**, not % shocks | series created from zero; % baseline undefined | high (structural) |
| AFF_DATA_INCOME | treat sign as **mixed/uncertain** | competition lowers cost, FX raised it | low |

## 8. Assumptions
1. Effects are **separable and combine** additively (pp) or multiplicatively (%); no interaction terms.
2. `lag` equals the **half-life** of the response; the shape is the same across events.
3. The **counterfactual is flat** — absent cataloged events an indicator would not move. (This
   attributes organic growth to events, and is why 2017→2021 organic gains are not represented.)
4. Comparable-country magnitudes **transfer** to Ethiopia up to a scalar attenuation.
5. Each link acts **independently** on its indicator.

## 9. Limitations & uncertainties
- **Single calibration point.** α and the fit rest on one 2021→2024 interval per indicator; only
  two indicators have enough history to validate at all.
- **Flat-counterfactual bias.** Organic/non-event growth is folded into event effects, inflating
  naive magnitudes (a second reason ownership over-predicts).
- **Long-lag policies unobservable yet.** NFIS-II, foreign-bank entry, EthioPay and the M-Pesa
  EthSwitch integration are recent or future; their effects can't be checked against data now.
- **Qualitative links carry no magnitude** by design, so enabling effects (e.g. the 2020 directive)
  are under-weighted in the arithmetic even though they were pivotal.
- **Direction of affordability is genuinely mixed**, so `AFF_DATA_INCOME` predictions are weak.

## 10. Handoff to forecasting (Task 4)
The calibrated, unit-aware effects + the half-life ramp become **event intervention terms**: Access
and Usage are projected as separate targets, imported ownership impacts enter attenuated, count
series (Telebirr/M-Pesa) are modeled as adoption curves, and all forecasts carry uncertainty bounds
sized to the confidence tags above.
