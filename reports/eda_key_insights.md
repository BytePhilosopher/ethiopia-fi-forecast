# EDA — Key Insights (Task 2)

**Author:** Yostina Abera  **Dataset:** `data/processed/ethiopia_fi_unified_data_enriched.csv` (87 records)
**Notebook:** [`notebooks/01_eda.ipynb`](../notebooks/01_eda.ipynb) · **Figures:** [`reports/figures/`](figures/)

Interpretation is anchored in **Sheet D — Market Nuances**: P2P is used for commerce (not
just person-to-person transfers), mobile-money-*only* users are ~0.5%, bank accounts are
already easily accessible, and credit penetration is very low.

---

## Insight 1 — Account ownership has plateaued despite a mobile-money boom
**Evidence.** Findex ownership: 22% (2014) → 35% (2017) → 46% (2021) → **49% (2024)**.
Annualized gain collapsed from **+4.3pp/yr (2014–17)** and +2.75pp/yr (2017–21) to
**+1.0pp/yr (2021–24)** — see `03_access_trajectory.png`, `04_growth_rates.png`. The
slowdown coincides with the *largest* supply push in Ethiopian history (Telebirr launch
2021, M-Pesa 2023, 55M+ registrations).
**So what.** The binding constraint is no longer account *supply*. Forecasts that extrapolate
the 2014–2021 slope will overshoot; ownership is approaching a demand-side ceiling.

## Insight 2 — The paradox is a measurement + market-structure artifact, not a data error
**Evidence.** Telebirr registered ~55M and M-Pesa ~10.8M accounts (≈65M), yet Findex
mobile-money *account ownership* is only 9.45% of adults (~6.6M people), and headline
any-account ownership rose just +3pp. Sheet D: mobile-money-only users ≈ 0.5%; bank
accounts are easily accessible.
**Interpretation.** Most mobile-money sign-ups went to people who **already had a bank
account**, so they add a payment channel but not a new *account holder*. Findex counts *any*
account, so the registrations are largely invisible to the headline metric.
**So what.** Model *ownership* and *usage* as distinct targets driven by different variables
(see Insight 4). Operator registration counts are a usage proxy, not an ownership proxy.

## Insight 3 — Registered ≠ active ≠ unique owner
**Evidence.** `07_registered_vs_active.png`: 54.8M Telebirr + 10.8M M-Pesa registered, but
M-Pesa 90-day **active** is 7.1M (a **66% active rate**), and enrichment shows agents
average **314 transactions/year (<1/day)**. Findex-implied unique owners ≈ 6.6M.
**So what.** Any forecast or KPI built on registration counts overstates inclusion by ~8–10×.
Active-rate and transactions-per-agent are the honest denominators.

## Insight 4 — Usage is going digital even though access stalled
**Evidence.** `08_p2p_vs_atm.png`: P2P transactions 49.7M (2024) → 128.3M (2025) overtook ATM
withdrawals (crossover ratio 1.08). P2P value reached ETB 577.7bn. Per Sheet D, much P2P is
merchant/commerce activity.
**So what.** The frontier has moved from "open an account" to "transact digitally." The most
forecastable growth signal is transaction volume, not ownership. This is the strongest
candidate dependent variable for the USAGE model.

## Insight 5 — The gender gap is device-driven
**Evidence.** `05_gender_gap.png`: account ownership gap narrowed from ~20pp (2021) to **15pp**
(men 57% vs women 42%, 2024). It tracks a **17pp phone-ownership gap** (men 50% vs women 33%)
and a 13pp digital-payment gap (men 26% vs women 13%).
**So what.** Closing the account gap is downstream of closing the *device* gap; gender-targeted
inclusion policy should lead with phone access, not account products.

## Insight 6 — Demand-side enablers are the ceiling and the best leading indicators
**Evidence.** `09_enablers.png`: 4G coverage nearly doubled (37.5%→70.8%, 2023→2025), yet phone
ownership is 41% and smartphone adoption 40% — far below coverage. Electricity access is 55%.
**So what.** Connectivity supply has run ahead of device demand. **Phone/smartphone ownership**
are the tightest near-term ceilings on both Access and Usage and the most promising *leading
indicators* for the next Findex round — more so than 4G coverage.

---

## Cross-cutting: what drives inclusion in Ethiopia?
From the `impact_link` relationship matrix (`11_impact_matrix.png`) and the trends above:
- **Enabling structural drivers** (slow, high-lag): the 2020 Payment Instrument Directive,
  NFIS-II, National Digital Payments Strategy, Fayda digital ID, foreign-bank entry.
- **Direct usage drivers** (fast): Telebirr/M-Pesa launches and EthSwitch/EthioPay
  interoperability → P2P volume and registered users.
- **Affordability shocks**: FX liberalization raised data cost (worse affordability);
  competition (Safaricom) pushes the other way.

## Hypotheses for the impact-modeling phase
1. Operator registrations predict **usage** (P2P volume) far better than **ownership**.
2. **Phone/smartphone ownership** is a stronger leading indicator of Findex ownership than 4G
   coverage — test with a lag.
3. NFIS-II and the 2020 directive behave as **enabling** (gradual) effects, not step-changes;
   model them as level shifts with long lags, not impulse spikes.
4. The account-ownership ceiling is ~ phone ownership; ownership cannot approach the NFIS-II
   70% target without the phone-ownership gap closing first.

## The data gaps that most limit these conclusions
See [`data_quality_assessment.md`](data_quality_assessment.md). In short: single-year
indicators dominate (**77%** — 23 of 30 indicators have data in only one year; just **7** have
≥2 distinct years), the multi-point series barely share years (so direct correlation is
infeasible), and there is no rural/urban disaggregation or pre-2021 mobile-money series.
