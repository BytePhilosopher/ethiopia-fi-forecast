"""Load and summarize the Ethiopia financial-inclusion datasets.

Loads all core datasets and returns them as tidy DataFrames:
  * unified records (observations, events, targets, impact_links)
  * reference codes (valid categorical values)

Usage:
    from src.load_data import load_all
    data = load_all(processed=True)   # or processed=False for the raw starter data
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"


def load_all(processed: bool = True) -> dict:
    """Return a dict of DataFrames: unified, observations, events, targets,
    impact_links, targets and reference_codes."""
    path = (PROC_DIR / "ethiopia_fi_unified_data_enriched.csv" if processed
            else RAW_DIR / "ethiopia_fi_unified_data.csv")
    unified = pd.read_csv(path)
    ref = pd.read_csv(RAW_DIR / "reference_codes.csv")

    return {
        "unified": unified,
        "observations": unified[unified.record_type == "observation"].copy(),
        "events": unified[unified.record_type == "event"].copy(),
        "targets": unified[unified.record_type == "target"].copy(),
        "impact_links": unified[unified.record_type == "impact_link"].copy(),
        "reference_codes": ref,
    }


def summary(processed: bool = True) -> None:
    d = load_all(processed=processed)
    print(f"Loaded {'processed' if processed else 'raw'} dataset: "
          f"{len(d['unified'])} unified records")
    print("  by record_type:", d["unified"]["record_type"].value_counts().to_dict())
    print(f"  reference_codes: {len(d['reference_codes'])} codes "
          f"across {d['reference_codes']['field'].nunique()} fields")
    obs = d["observations"]
    print(f"  observations span: {obs.observation_date.min()} -> {obs.observation_date.max()}")
    print(f"  distinct indicators: {obs.indicator_code.nunique()}")


if __name__ == "__main__":
    print("=== RAW (starter) ===")
    summary(processed=False)
    print("\n=== PROCESSED (enriched + corrected) ===")
    summary(processed=True)
