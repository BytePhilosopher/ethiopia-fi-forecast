"""
Build the analysis-ready (processed) unified dataset for the Ethiopia
financial-inclusion forecast.

Pipeline
--------
1. Load the faithful raw unified CSV (starter data, 57 records).
2. Correct a column-alignment defect in the starter main sheet
   (observation / event / target rows only) — see fix_doc_alignment().
3. Append the Task-1 enrichment records (observations, events, impact_links)
   defined in ENRICHMENT below, each grounded in a cited public source.
4. Write data/processed/ethiopia_fi_unified_data_enriched.csv.

Run:  python src/build_processed_dataset.py
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "ethiopia_fi_unified_data.csv"
OUT = ROOT / "data" / "processed" / "ethiopia_fi_unified_data_enriched.csv"

COLLECTOR = "Yostina Abera"
COLLECTED_ON = "2026-07-18"

# Canonical unified column order (superset incl. parent_id).
COLUMNS = [
    "record_id", "parent_id", "record_type", "category", "pillar", "indicator",
    "indicator_code", "indicator_direction", "value_numeric", "value_text",
    "value_type", "unit", "observation_date", "period_start", "period_end",
    "fiscal_year", "gender", "location", "region", "source_name", "source_type",
    "source_url", "confidence", "related_indicator", "relationship_type",
    "impact_direction", "impact_magnitude", "impact_estimate", "lag_months",
    "evidence_basis", "comparable_country", "collected_by", "collection_date",
    "original_text", "notes",
]


def fix_doc_alignment(df: pd.DataFrame) -> pd.DataFrame:
    """Correct the one-column rightward shift in the starter *main* sheet.

    In the starter file the documentation columns of observation/event/target
    rows were entered one column to the left of their header, so:
        comparable_country held the collector name ("Example_Trainee"),
        collected_by       held the collection date,
        collection_date    held the source quote,
        original_text      held the short note,
        notes              was empty.
    Impact_link rows are already aligned correctly and are left untouched.
    The pre-existing `notes` column is empty on main rows, so the fix is lossless.
    """
    df = df.copy()
    mask = df["record_type"].isin(["observation", "event", "target"])
    idx = df.index[mask]
    df.loc[idx, "notes"] = df.loc[idx, "original_text"].values
    df.loc[idx, "original_text"] = df.loc[idx, "collection_date"].values
    df.loc[idx, "collection_date"] = df.loc[idx, "collected_by"].values
    df.loc[idx, "collected_by"] = df.loc[idx, "comparable_country"].values
    df.loc[idx, "comparable_country"] = pd.NA  # observations carry no comparable country
    return df


# --- Source shorthands (kept DRY) -------------------------------------------
FINDEX25 = ("Global Findex 2025", "survey",
            "https://www.worldbank.org/en/publication/globalfindex")
ETHIOTEL = ("Ethio Telecom", "operator", "https://www.ethiotelecom.et/")
NBE_FSR = ("NBE Financial Stability Report Nov 2024", "regulator",
           "https://nbe.gov.et/wp-content/uploads/2024/11/Financial-Stability-Report_NOV2024.pdf")
SHEGA = ("Shega / DFS Ethiopia Hub", "research",
         "https://digitalfinance.shega.co/insights/articles/the-rise-of-mobile-money-in-ethiopia-without-the-agents")
GSMA = ("GSMA Mobile Economy Sub-Saharan Africa 2024", "research",
        "https://www.gsmaintelligence.com/research/accelerating-smartphone-adoption-in-africa")
WB_WDI = ("World Bank World Development Indicators", "research",
          "https://data.worldbank.org/indicator/EG.ELC.ACCS.ZS?locations=ET")
NBE = ("National Bank of Ethiopia", "regulator", "https://nbe.gov.et/")
ADDIS = ("Addis Insight", "news",
         "https://www.addisinsight.net/2024/12/17/ethiopia-opens-doors-to-foreign-banks-landmark-proclamation-paves-the-way-for-international-investment/")


def obs(rid, pillar, ind, code, direction, val, vtype, unit, date, src,
        conf, orig, note, gender="all", location="national", region=None):
    name, stype, url = src
    return dict(record_id=rid, record_type="observation", pillar=pillar,
                indicator=ind, indicator_code=code, indicator_direction=direction,
                value_numeric=val, value_type=vtype, unit=unit,
                observation_date=date, fiscal_year=int(date[:4]), gender=gender,
                location=location, region=region, source_name=name,
                source_type=stype, source_url=url, confidence=conf,
                collected_by=COLLECTOR, collection_date=COLLECTED_ON,
                original_text=orig, notes=note)


def event(rid, cat, name, code, date, src, conf, orig, note):
    sname, stype, url = src
    return dict(record_id=rid, record_type="event", category=cat, indicator=name,
                indicator_code=code, value_text="Occurred", value_type="categorical",
                observation_date=date, fiscal_year=int(date[:4]), gender="all",
                location="national", source_name=sname, source_type=stype,
                source_url=url, confidence=conf, collected_by=COLLECTOR,
                collection_date=COLLECTED_ON, original_text=orig, notes=note)


def link(rid, parent, pillar, rel_ind, reltype, direction, mag, est, lag,
         basis, note, country=None, conf="medium"):
    return dict(record_id=rid, parent_id=parent, record_type="impact_link",
                pillar=pillar, related_indicator=rel_ind, relationship_type=reltype,
                impact_direction=direction, impact_magnitude=mag, impact_estimate=est,
                lag_months=lag, evidence_basis=basis, comparable_country=country,
                confidence=conf, collected_by=COLLECTOR, collection_date=COLLECTED_ON,
                notes=note)


ENRICHMENT = [
    # ---------------- OBSERVATIONS ----------------
    # Findex 2025 gender-disaggregated account ownership (extends existing 2021 split)
    obs("REC_0034", "ACCESS", "Account Ownership Rate", "ACC_OWNERSHIP", "higher_better",
        57.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "57 percent of men in Ethiopia report having an account",
        "Findex 2025 male account ownership; extends gender series with 2021 (REC_0004).",
        gender="male"),
    obs("REC_0035", "ACCESS", "Account Ownership Rate", "ACC_OWNERSHIP", "higher_better",
        42.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "only 42 percent of women do",
        "Findex 2025 female account ownership; pairs with REC_0034 (gap = 15pp).",
        gender="female"),
    # Mobile phone ownership (key access enabler for DFS) + gender split
    obs("REC_0036", "ACCESS", "Mobile Phone Ownership", "ACC_PHONE_OWN", "higher_better",
        41.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "only 41 percent of adults own a mobile phone",
        "Device access is the binding constraint on DFS uptake; low by regional standards."),
    obs("REC_0037", "GENDER", "Mobile Phone Ownership (Male)", "ACC_PHONE_OWN", "higher_better",
        50.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "50 percent of men [own a phone]",
        "Male device ownership for gender-gap analysis.", gender="male"),
    obs("REC_0038", "GENDER", "Mobile Phone Ownership (Female)", "ACC_PHONE_OWN", "higher_better",
        33.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "just 33 percent of women [own a phone]",
        "Female device ownership; phone gender gap = 17pp, a driver of the account gap.",
        gender="female"),
    # Digital payments (usage of DFS) overall + gender
    obs("REC_0039", "USAGE", "Made or Received Digital Payment", "USG_DIGITAL_PAY", "higher_better",
        21.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "21 percent using digital payments",
        "Findex 2025 digital-payment usage; the maturity gap behind headline account ownership."),
    obs("REC_0040", "GENDER", "Made or Received Digital Payment (Male)", "USG_DIGITAL_PAY", "higher_better",
        26.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "Only 26 percent of men...used digital payments in the past year",
        "Male digital-payment usage.", gender="male"),
    obs("REC_0041", "GENDER", "Made or Received Digital Payment (Female)", "USG_DIGITAL_PAY", "higher_better",
        13.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "13 percent of women used digital payments in the past year",
        "Female digital-payment usage; usage gender gap = 13pp.", gender="female"),
    # Depth: savings & borrowing (beyond payments)
    obs("REC_0042", "DEPTH", "Saved in a Financial Account", "DEP_SAVED", "higher_better",
        36.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "36 percent saved in account",
        "DEPTH indicator: savings behaviour beyond transactional accounts."),
    obs("REC_0043", "DEPTH", "Borrowed from a Financial Institution", "DEP_BORROWED", "higher_better",
        4.0, "percentage", "%", "2024-11-29", FINDEX25, "high",
        "Just four percent reported borrowing",
        "Very low credit penetration — matches Market Nuance D (thin credit market)."),
    # Telebirr user time series (builds a real growth curve for USAGE forecasting)
    obs("REC_0044", "USAGE", "Telebirr Registered Users", "USG_TELEBIRR_USERS", "higher_better",
        20_000_000, "count", "users", "2022-07-31", ETHIOTEL, "high",
        "surpassed 20 million subscribers by July 2022",
        "Adds early point to Telebirr series (only 2025 present in starter data)."),
    obs("REC_0045", "USAGE", "Telebirr Registered Users", "USG_TELEBIRR_USERS", "higher_better",
        34_300_000, "count", "users", "2023-06-30", ETHIOTEL, "high",
        "34.3 million subscribers by mid-2023",
        "Mid-point of Telebirr adoption curve."),
    obs("REC_0046", "USAGE", "Telebirr Registered Users", "USG_TELEBIRR_USERS", "higher_better",
        47_500_000, "count", "users", "2024-06-30", ETHIOTEL, "high",
        "Telebirr subscribers reached 47.5 million achieving 107% of target (FY2023/24)",
        "Completes 4-point Telebirr series 2022-2025 for trend estimation."),
    # Infrastructure (NBE) — ATMs & POS
    obs("REC_0047", "ACCESS", "ATM Terminals Deployed", "ACC_ATM_COUNT", "higher_better",
        10_551, "count", "terminals", "2024-06-30", NBE_FSR, "high",
        "the number of ATMs across Ethiopia grew by 34.2%, reaching a total of 10,551",
        "Cash-out infrastructure; supports agent-vs-ATM crossover analysis (USG_CROSSOVER)."),
    obs("REC_0048", "ACCESS", "POS Terminals Deployed", "ACC_POS_COUNT", "higher_better",
        14_030, "count", "terminals", "2024-06-30", NBE_FSR, "high",
        "the number of POS terminals rose by 16.7%, reaching 14,030",
        "Merchant-acceptance infrastructure; enabler for digital-payment usage."),
    # Agent network + utilization (quality)
    obs("REC_0049", "ACCESS", "Mobile Money Agents", "ACC_MM_AGENTS", "higher_better",
        216_000, "count", "agents", "2024-06-30", SHEGA, "medium",
        "Ethio telecom had around 216,000 agents as of June 2024",
        "Cash-in/cash-out reach; largest agent network in the market."),
    obs("REC_0050", "QUALITY", "Transactions per Agent per Year", "QLT_AGENT_TXN", "higher_better",
        314, "count", "transactions", "2024-12-31", SHEGA, "medium",
        "the average number of transactions an agent made in the year was just 314",
        "Utilization/quality: high agent count but <1 txn/day — dormant-agent problem (Nuance D)."),
    # Enablers (indirect correlation)
    obs("REC_0051", "ACCESS", "Smartphone Adoption", "ACC_SMARTPHONE", "higher_better",
        40.0, "percentage", "%", "2023-12-31", GSMA, "medium",
        "smartphone adoption of 40% in 2023",
        "Smartphone base caps app-based DFS; GSMA forecasts 50% by 2030."),
    obs("REC_0052", "ACCESS", "Unique Mobile Subscriber Penetration", "ACC_SUB_PEN", "higher_better",
        36.0, "percentage", "%", "2023-12-31", GSMA, "medium",
        "subscriber penetration of 36% in 2023",
        "Unique-subscriber reach (below SSA average) — structural ceiling on mobile money."),
    obs("REC_0053", "ACCESS", "Access to Electricity", "ENAB_ELECTRICITY", "higher_better",
        55.4, "percentage", "%", "2023-12-31", WB_WDI, "medium",
        "As of 2023, 55.4% of Ethiopia's population has access to electricity",
        "Enabler proxy: power access constrains phone charging / agent operations, esp. rural."),

    # ---------------- EVENTS ----------------
    event("EVT_0011", "regulation", "NBE Payment Instrument Issuers Directive (ONPS/01/2020)",
          "EVT_PII_DIRECTIVE", "2020-04-01", NBE, "high",
          "NBE directive licensing non-bank Payment Instrument Issuers",
          "Legal basis that allowed Telebirr (2021) and M-Pesa (2023) to issue mobile money — foundational enabler."),
    event("EVT_0012", "policy", "National Digital Payments Strategy 2021-2024",
          "EVT_NDPS", "2021-01-01", NBE, "high",
          "NBE National Digital Payments Strategy (2021-2024)",
          "Set the roadmap for cashless transition and instant-payment rails (EthSwitch/EthioPay)."),
    event("EVT_0013", "policy", "Banking Business Proclamation No. 1360/2024 (Foreign Bank Entry)",
          "EVT_FOREIGN_BANKS", "2024-12-17", ADDIS, "high",
          "Parliament approved Banking Business Proclamation No. 1360/2024 allowing foreign banks after 50 years",
          "Opens the sector to foreign competition/capital; medium-term driver of access, competition and credit depth."),

    # ---------------- IMPACT LINKS ----------------
    # New events -> indicators
    link("IMP_0015", "EVT_0011", "ACCESS", "ACC_MM_ACCOUNT", "enabling", "increase",
         "high", None, 15, "theoretical",
         "Directive created the legal category under which mobile money accounts could be issued."),
    link("IMP_0016", "EVT_0011", "USAGE", "USG_TELEBIRR_USERS", "enabling", "increase",
         "high", None, 15, "theoretical",
         "Without the 2020 licensing regime Telebirr could not have launched/scaled."),
    link("IMP_0017", "EVT_0012", "USAGE", "USG_DIGITAL_PAY", "direct", "increase",
         "medium", 10, 18, "theoretical",
         "National strategy coordinated rails and merchant acceptance driving digital-payment uptake."),
    link("IMP_0018", "EVT_0013", "ACCESS", "ACC_OWNERSHIP", "indirect", "increase",
         "medium", 5, 36, "literature",
         "Foreign bank entry expands branch/product competition; Kenyan liberalization raised access over ~3-5 yrs.",
         country="Kenya"),
    link("IMP_0019", "EVT_0013", "DEPTH", "DEP_BORROWED", "indirect", "increase",
         "medium", 8, 36, "literature",
         "New entrants/capital typically deepen credit supply from a very low base.",
         country="Kenya"),
    # Gap-fill: existing events that had no impact links in the starter data
    link("IMP_0020", "EVT_0009", "ACCESS", "ACC_OWNERSHIP", "enabling", "increase",
         "medium", 8, 12, "theoretical",
         "NFIS-II sets the 70% ownership target and coordinates interventions (gap-fill for EVT_0009)."),
    link("IMP_0021", "EVT_0009", "GENDER", "GEN_MM_SHARE", "enabling", "increase",
         "medium", 6, 24, "theoretical",
         "NFIS-II includes gender-inclusion goals feeding the 50% women-MM-share target (gap-fill for EVT_0009)."),
]


def main():
    raw = pd.read_csv(RAW, dtype=str)
    raw = fix_doc_alignment(raw)

    add = pd.DataFrame(ENRICHMENT)
    # keep numeric-looking columns as-is; align to canonical schema
    combined = pd.concat([raw, add], ignore_index=True)
    combined = combined.reindex(columns=COLUMNS)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUT, index=False)

    print(f"Wrote {OUT.relative_to(ROOT)}  ->  {combined.shape[0]} records")
    print("By record_type:", combined["record_type"].value_counts().to_dict())
    print(f"Enrichment added: {len(add)} records "
          f"({(add['record_type']=='observation').sum()} obs, "
          f"{(add['record_type']=='event').sum()} events, "
          f"{(add['record_type']=='impact_link').sum()} impact_links)")


if __name__ == "__main__":
    main()
