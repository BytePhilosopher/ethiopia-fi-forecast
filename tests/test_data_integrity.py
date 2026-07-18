"""Data-integrity tests for the enriched unified dataset.

These lock in the Task-1 guarantees: valid schema, valid categorical codes,
referential integrity of impact_links, and correct provenance on enriched rows.
"""
from pathlib import Path
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed" / "ethiopia_fi_unified_data_enriched.csv"
REF = ROOT / "data" / "raw" / "reference_codes.csv"

CATEGORICAL_FIELDS = {
    "record_type": "record_type", "category": "category", "pillar": "pillar",
    "indicator_direction": "indicator_direction", "value_type": "value_type",
    "source_type": "source_type", "confidence": "confidence", "gender": "gender",
    "location": "location", "relationship_type": "relationship_type",
    "impact_direction": "impact_direction", "impact_magnitude": "impact_magnitude",
    "evidence_basis": "evidence_basis",
}


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(PROCESSED, dtype=str)


@pytest.fixture(scope="module")
def ref():
    return pd.read_csv(REF, dtype=str)


def test_files_exist():
    assert PROCESSED.exists() and REF.exists()


def test_record_type_counts(df):
    counts = df["record_type"].value_counts().to_dict()
    assert counts == {"observation": 50, "impact_link": 21, "event": 13, "target": 3}


@pytest.mark.parametrize("col", list(CATEGORICAL_FIELDS))
def test_categorical_values_are_valid(df, ref, col):
    valid = set(ref[ref["field"] == CATEGORICAL_FIELDS[col]]["code"])
    used = set(df[col].dropna())
    assert used <= valid, f"{col} has invalid codes: {used - valid}"


def test_events_have_no_pillar(df):
    """Schema rule: events are neutral — pillar must be empty."""
    assert df[df.record_type == "event"]["pillar"].isna().all()


def test_impact_links_reference_real_events(df):
    events = set(df[df.record_type == "event"]["record_id"])
    parents = set(df[df.record_type == "impact_link"]["parent_id"].dropna())
    assert parents <= events, f"orphan impact_links: {parents - events}"


def test_observations_have_value_and_date(df):
    obs = df[df.record_type == "observation"]
    assert obs["value_numeric"].notna().all()
    assert obs["observation_date"].notna().all()


def test_enriched_rows_have_provenance(df):
    new = df[df["collected_by"] == "Yostina Abera"]
    assert len(new) == 30
    assert new["collection_date"].eq("2026-07-18").all()
    # observations & events cite a source URL; impact_links carry evidence_basis instead
    obs_ev = new[new.record_type.isin(["observation", "event"])]
    assert obs_ev["source_url"].notna().all()
    links = new[new.record_type == "impact_link"]
    assert links["evidence_basis"].notna().all()
