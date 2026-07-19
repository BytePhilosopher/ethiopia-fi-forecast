# Data Quality Assessment (Task 2)

**Author:** Yostina Abera  **Dataset:** `data/processed/ethiopia_fi_unified_data_enriched.csv` (87 records)

This documents the limitations that constrain the EDA and the subsequent forecasting, and
the one correction already applied to the starter data.

---

## 1. Confidence profile
Most records are high-confidence official/operator figures; enrichment enablers (GSMA, World
Bank dashboard, Shega/UNCDF) are medium.

| Confidence | Meaning | Notes |
|-----------|---------|-------|
| high | primary/official, quoted verbatim | Findex, Ethio Telecom, NBE FSR, NIDP |
| medium | reputable secondary / light interpretation | GSMA, Shega, WB WDI, some derived gaps |
| low / estimated | — | not used in the enriched observations |

~80% of observations are high-confidence, so the *values* are trustworthy; the limitations
below are about **coverage and structure**, not accuracy.

## 2. Sparsity — the dominant limitation
- **30 indicators, but only 7 span ≥2 distinct years** (77% are single-year snapshots):
  `ACC_OWNERSHIP` (2014/17/21/24), `USG_TELEBIRR_USERS` (2022–25), `ACC_MM_ACCOUNT`,
  `ACC_4G_COV`, `ACC_FAYDA`, `GEN_GAP_ACC`, `USG_P2P_COUNT`.
- **Only ACC_OWNERSHIP has a real pre-2021 history** (from 2014). Everything else is
  concentrated in 2024–2025.
- **Consequence for modeling:** classical time-series methods (ARIMA, trend + seasonality)
  are not viable per indicator. Forecasting must lean on the event/impact-link structure,
  comparable-country priors, and a small number of anchored trend points with wide bounds.

## 3. Non-overlapping years → direct correlation is unreliable
The two richest series barely coincide: account ownership is observed in 2014/17/21/24,
Telebirr users in 2022/23/24/25 — a **single** overlapping year (2024). Cross-indicator
Pearson/Spearman correlation would therefore be computed on n≈1–2 and is **not reported**;
relationships are instead read from `impact_link` records (see `11_impact_matrix.png`).

## 4. Definitional / comparability hazards
- **Registered vs active vs unique owner.** Operator "users" (Telebirr 54.8M) are registered
  wallets; Findex "mobile-money account ownership" (9.45%) is survey-based unique adults; M-Pesa
  "active" is 90-day. These are **not interchangeable** and must never be plotted on one axis
  or differenced. (This is exactly the confusion behind the +3pp paradox.)
- **Fiscal vs calendar year.** Ethio Telecom / NBE report on an Ethiopian fiscal year
  (≈ 8 July–7 July); Findex is calendar-year survey fieldwork (Oct–Nov 2024). Dates were kept
  as reported; small alignment error is possible when joining operator and survey data.
- **AFF_DATA_INCOME direction.** "Data cost as % of GNI" is *lower-is-better*; an "increase"
  in the impact matrix means **worse** affordability. Direction must be handled explicitly.
- **Adult-population denominator.** The "unique owners ≈ 6.6M" figure uses ~70M adults (15+),
  an estimate; the dataset's own note cites 152.7M *total* population. Treat the 6.6M as
  order-of-magnitude, not exact.

## 5. Coverage gaps (missing but wanted)
- **No rural/urban disaggregation** for ownership or usage — limits the access-geography story
  that Sheet D flags as central.
- **No pre-2021 mobile-money series** — cannot see the Telebirr take-off from a true zero base.
- **Thin QUALITY & TRUST pillars** — QUALITY has one enrichment point (agent txns/yr); TRUST has
  no observations at all (fraud/complaints unmeasured).
- **No wages/G2P or merchant-payment breakdown** — use-case mix (P2P vs merchant vs bill) is
  inferred from Sheet D, not measured.
- **Literacy & urbanization** deliberately omitted from enrichment (no URL-backed figure found)
  — both are relevant enablers still missing.

## 6. Correction already applied (starter data)
The starter *main* sheet (observation/event/target rows) had its five documentation columns
shifted one position left of their headers — `comparable_country` held the collector name
("Example_Trainee"), `collected_by` held a date, `collection_date` held the source quote, and
`original_text` held the note. `src/build_processed_dataset.py :: fix_doc_alignment()` restores
the intended alignment (the pre-existing `notes` column was empty, so the fix is lossless).
Impact-link rows were already aligned and were left untouched. Full detail in
[`data_enrichment_log.md`](../data_enrichment_log.md).

## 7. Net effect on the forecast (how we compensate)
| Limitation | Mitigation in later phases |
|-----------|----------------------------|
| Too few time points | event/impact-link-driven modeling + comparable-country priors; wide confidence bounds |
| Non-overlapping years | avoid cross-series correlation; align on the few shared anchors only |
| Registered≠owner | model ownership and usage separately; use active-rate adjustments |
| No rural/urban / TRUST | flag as out-of-scope; recommend Findex microdata + NBE complaints data as next enrichment |
