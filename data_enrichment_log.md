# Data Enrichment Log — Task 1

**Project:** Ethiopia Financial Inclusion Forecast
**Author:** Yostina Abera
**Collection date:** 2026-07-18
**Starter dataset:** `data/raw/ethiopia_fi_unified_data.csv` (57 records)
**Deliverable dataset:** `data/processed/ethiopia_fi_unified_data_enriched.csv` (87 records) — also exported as `.xlsx`

---

## 1. Summary of changes

| Record type   | Starter | Added | Final |
|---------------|:------:|:-----:|:-----:|
| observation   | 30 | **+20** | 50 |
| event         | 10 | **+3**  | 13 |
| impact_link   | 14 | **+7**  | 21 |
| target        | 3  |  0      | 3  |
| **Total**     | **57** | **+30** | **87** |

Plus **1 systematic data-quality correction** applied to all starter observation/event/target rows (Section 4).

All new records were validated against `data/raw/reference_codes.csv`: every categorical
field (`record_type`, `category`, `pillar`, `value_type`, `source_type`, `confidence`,
`gender`, `location`, `relationship_type`, `impact_direction`, `impact_magnitude`,
`evidence_basis`) uses an approved code, all `impact_link.parent_id` values resolve to a
real event, and the build is reproducible via `python src/build_processed_dataset.py`.

---

## 2. Reproducibility

The processed dataset is **generated**, not hand-edited, so the enrichment is auditable:

```
data/raw/ethiopia_fi_unified_data.csv   # faithful conversion of the starter .xlsx (unchanged)
        │
        ▼  src/build_processed_dataset.py   (correction + enrichment, both documented in code)
        ▼
data/processed/ethiopia_fi_unified_data_enriched.csv   # analysis-ready
```

The raw file is a faithful CSV conversion of the two-sheet starter workbook
(`ethiopia_fi_unified_data` + `Impact_sheet` merged into one unified schema with a
`parent_id` column). It is **never modified** — all corrections and additions happen
downstream in the build script.

---

## 3. Design rationale — what to enrich and why

The forecasting task targets **Access** (can people reach services?) and **Usage** (are
people actually transacting?). Guided by the *Additional Data Points Guide*, I prioritised
data that (a) turns single-point indicators into **time series** the models can fit, (b)
adds the **direct-correlation** infrastructure the guide flags (agents, ATMs, POS), and (c)
adds **enabler proxies** (phones, smartphones, electricity) that cap how far Access/Usage
can realistically grow. I also captured **Ethiopia-specific nuances** (thin credit market,
dormant agents, the access-vs-usage maturity gap).

---

## 4. Data-quality correction (applied to starter data)

**Issue.** In the starter *main* sheet (observations, events, targets — **not** impact_links),
the five documentation columns were entered one position to the **left** of their header.
Concretely, for every such row:

| Column (header) | Held (starter, wrong) | Should hold |
|-----------------|-----------------------|-------------|
| `comparable_country` | `"Example_Trainee"` (a collector name) | *(empty for observations)* |
| `collected_by`       | `2025-01-20` (a date)          | collector name |
| `collection_date`    | source quote                   | the date |
| `original_text`      | short note                     | the source quote |
| `notes`              | *(empty)*                      | the note |

The impact_link rows (from `Impact_sheet`) were **correctly** aligned
(`comparable_country` = Kenya/India/Tanzania, `collected_by` = Example_Trainee,
`notes` = evidence text), so the fix is scoped to main-sheet rows only.

**Fix.** `fix_doc_alignment()` shifts the four affected values one column right into their
correct semantic field and clears `comparable_country` for observations. The pre-existing
`notes` column was empty on all main rows, so **no data is lost**.

**Why it matters.** Without the fix, `collected_by` looks like a date and every observation
carries a phantom `comparable_country`, which would corrupt provenance filtering and any
join on those fields.

---

## 5. New observations (20)

Collector = *Yostina Abera*; collection_date = *2026-07-18* on all rows.
`original_text` = exact quote from the cited source; full provenance in the CSV.

### 5a. Findex 2025 — gender & maturity detail (pillar coverage)
| record_id | indicator_code | pillar | value | gender | source | conf |
|-----------|----------------|--------|------:|--------|--------|------|
| REC_0034 | ACC_OWNERSHIP | ACCESS | 57% | male | Global Findex 2025 | high |
| REC_0035 | ACC_OWNERSHIP | ACCESS | 42% | female | Global Findex 2025 | high |
| REC_0036 | ACC_PHONE_OWN | ACCESS | 41% | all | Global Findex 2025 | high |
| REC_0037 | ACC_PHONE_OWN | GENDER | 50% | male | Global Findex 2025 | high |
| REC_0038 | ACC_PHONE_OWN | GENDER | 33% | female | Global Findex 2025 | high |
| REC_0039 | USG_DIGITAL_PAY | USAGE | 21% | all | Global Findex 2025 | high |
| REC_0040 | USG_DIGITAL_PAY | GENDER | 26% | male | Global Findex 2025 | high |
| REC_0041 | USG_DIGITAL_PAY | GENDER | 13% | female | Global Findex 2025 | high |
| REC_0042 | DEP_SAVED | DEPTH | 36% | all | Global Findex 2025 | high |
| REC_0043 | DEP_BORROWED | DEPTH | 4% | all | Global Findex 2025 | high |

*Why useful:* extends the gender split (starter only had 2021) to 2024; adds the **usage
maturity gap** (49% own an account but only 21% make digital payments) and the DEPTH pillar
(savings/credit), which the starter data did not cover at all. The 4% borrowing figure is
direct evidence for Market Nuance D (very thin credit market).
*Source:* World Bank Global Findex 2025 — https://www.worldbank.org/en/publication/globalfindex

### 5b. Telebirr user time series (Usage — turns 1 point into 4)
| record_id | indicator_code | date | value | conf |
|-----------|----------------|------|------:|------|
| REC_0044 | USG_TELEBIRR_USERS | 2022-07-31 | 20,000,000 | high |
| REC_0045 | USG_TELEBIRR_USERS | 2023-06-30 | 34,300,000 | high |
| REC_0046 | USG_TELEBIRR_USERS | 2024-06-30 | 47,500,000 | high |

*Why useful:* the starter data had only the 2025 Telebirr figure. These three prior points
create a **4-point adoption curve (2022→2025)** — enough to fit an S-curve/growth trend for
the dominant usage driver.
*Source:* Ethio Telecom performance reporting — https://www.ethiotelecom.et/

### 5c. Infrastructure & agent network (direct-correlation, Guide Sheet B)
| record_id | indicator_code | pillar | value | source | conf |
|-----------|----------------|--------|------:|--------|------|
| REC_0047 | ACC_ATM_COUNT | ACCESS | 10,551 | NBE FSR Nov 2024 | high |
| REC_0048 | ACC_POS_COUNT | ACCESS | 14,030 | NBE FSR Nov 2024 | high |
| REC_0049 | ACC_MM_AGENTS | ACCESS | 216,000 | Shega / UNCDF | medium |
| REC_0050 | QLT_AGENT_TXN | QUALITY | 314 | Shega / UNCDF | medium |

*Why useful:* ATM/POS counts are the acceptance/cash-out backbone behind the P2P-vs-ATM
crossover already in the data. Agent count + the **314 transactions/agent/year** figure
capture the "large but dormant agent network" nuance — a QUALITY signal (the starter data
had no QUALITY observations).
*Sources:* NBE Financial Stability Report Nov 2024 —
https://nbe.gov.et/wp-content/uploads/2024/11/Financial-Stability-Report_NOV2024.pdf ;
Shega DFS Ethiopia Hub — https://digitalfinance.shega.co/insights/articles/the-rise-of-mobile-money-in-ethiopia-without-the-agents

### 5d. Enabler proxies (indirect-correlation, Guide Sheet C)
| record_id | indicator_code | pillar | value | date | source | conf |
|-----------|----------------|--------|------:|------|--------|------|
| REC_0051 | ACC_SMARTPHONE | ACCESS | 40% | 2023 | GSMA ME SSA 2024 | medium |
| REC_0052 | ACC_SUB_PEN | ACCESS | 36% | 2023 | GSMA ME SSA 2024 | medium |
| REC_0053 | ENAB_ELECTRICITY | ACCESS | 55.4% | 2023 | World Bank WDI | medium |

*Why useful:* these are the **structural ceilings** on Access/Usage. Only 41% own a phone
and 40% a smartphone, so app-based DFS cannot outrun device access; electricity (55%)
constrains rural charging and agent operations. Essential context for realistic forecast
bounds.
*Sources:* GSMA Mobile Economy SSA 2024 —
https://www.gsmaintelligence.com/research/accelerating-smartphone-adoption-in-africa ;
World Bank WDI — https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS?locations=ET

---

## 6. New events (3)

Events follow the schema rule: `category` is set, **`pillar` is left empty** (no
pre-assignment). Effects are modelled via impact_links in Section 7.

| record_id | category | event | date | source | conf |
|-----------|----------|-------|------|--------|------|
| EVT_0011 | regulation | NBE Payment Instrument Issuers Directive (ONPS/01/2020) | 2020-04-01 | NBE | high |
| EVT_0012 | policy | National Digital Payments Strategy 2021–2024 | 2021-01-01 | NBE | high |
| EVT_0013 | policy | Banking Business Proclamation No. 1360/2024 (foreign bank entry) | 2024-12-17 | Addis Insight | high |

*Why useful:*
- **EVT_0011** is the *foundational enabler* — the 2020 directive created the legal category
  of non-bank Payment Instrument Issuer that made Telebirr (2021) and M-Pesa (2023) possible.
  It predates and explains the launches already in the data.
- **EVT_0012** is the national roadmap coordinating the instant-payment rails
  (EthSwitch/EthioPay) already catalogued.
- **EVT_0013** opens the sector to foreign banks after 50 years — a medium-term structural
  driver of access, competition and credit depth.

*Sources:* NBE — https://nbe.gov.et/ ; Addis Insight —
https://www.addisinsight.net/2024/12/17/ethiopia-opens-doors-to-foreign-banks-landmark-proclamation-paves-the-way-for-international-investment/

---

## 7. New impact_links (7)

`pillar` = pillar of the affected indicator; `evidence_basis` and `comparable_country`
document the estimate's grounding.

| record_id | parent (event) | pillar | related_indicator | direction | magnitude | lag (mo) | basis | comp. country |
|-----------|----------------|--------|-------------------|-----------|-----------|:-------:|-------|---------------|
| IMP_0015 | EVT_0011 | ACCESS | ACC_MM_ACCOUNT | increase | high | 15 | theoretical | — |
| IMP_0016 | EVT_0011 | USAGE | USG_TELEBIRR_USERS | increase | high | 15 | theoretical | — |
| IMP_0017 | EVT_0012 | USAGE | USG_DIGITAL_PAY | increase | medium | 18 | theoretical | — |
| IMP_0018 | EVT_0013 | ACCESS | ACC_OWNERSHIP | increase | medium | 36 | literature | Kenya |
| IMP_0019 | EVT_0013 | DEPTH | DEP_BORROWED | increase | medium | 36 | literature | Kenya |
| IMP_0020 | EVT_0009 (NFIS-II) | ACCESS | ACC_OWNERSHIP | increase | medium | 12 | theoretical | — |
| IMP_0021 | EVT_0009 (NFIS-II) | GENDER | GEN_MM_SHARE | increase | medium | 24 | theoretical | — |

*Why useful:*
- IMP_0015/16/17 wire the new **enabling** policy events to the indicators they unlocked.
- IMP_0018/19 model the delayed, literature-based effect of foreign-bank liberalisation
  (Kenya as comparator).
- **IMP_0020/21 are gap-fills:** the starter data catalogued NFIS-II (EVT_0009) and the
  P2P-crosses-ATM milestone (EVT_0006) but attached **no impact_links to NFIS-II** — the
  single most important national policy for the 70% ownership and 50% women-MM-share targets.
  These links connect the strategy to the two targets it governs.

---

## 8. Confidence conventions

- **high** — primary/official source, figure quoted verbatim (Findex, Ethio Telecom, NBE FSR).
- **medium** — reputable secondary source or an official figure requiring light interpretation
  (GSMA, Shega/UNCDF, World Bank WDI dashboard).
- Impact_link magnitudes are qualitative bands (per reference_codes) with a numeric
  `impact_estimate` only where a comparable-country figure supports it; `evidence_basis`
  records whether the estimate is `empirical`, `literature` or `theoretical`.

## 9. Known limitations / candidates for further enrichment

- **Not added (no URL-backed figure found):** adult literacy rate and urbanisation %
  (both relevant enablers). Left out rather than guessed, to keep provenance clean.
- Region-level (rural/urban) Findex disaggregation would sharpen the access model but
  requires the Findex 2025 microdata rather than the summary release.
- M-Pesa Ethiopia lacks a multi-year series (only the 2024 point exists); worth adding once
  Safaricom publishes comparable annual figures.
