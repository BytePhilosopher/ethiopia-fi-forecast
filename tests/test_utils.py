"""Tests for the shared utilities in src/utils.py (Engineering task).

These helpers were extracted from duplicated code in eda/impact_model/forecast, so the
maths they encode (the half-life ramp in particular) is now covered in exactly one place.
"""
import numpy as np
import pandas as pd
import pytest

from src.utils import (DAYS_PER_MONTH, DAYS_PER_YEAR, PALETTE, half_life_fraction,
                       months_between, observation_series, years_between)
from src.load_data import load_all


# ----------------------------------------------------------------- time helpers
def test_months_and_years_between_are_signed():
    a, b = pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01")   # 365 days, no leap day
    assert years_between(b, a) == pytest.approx(365 / DAYS_PER_YEAR, abs=1e-6)
    assert months_between(b, a) == pytest.approx(365 / DAYS_PER_MONTH, abs=1e-6)
    # reversing the arguments flips the sign — callers rely on this for pre-event dates
    assert years_between(a, b) == pytest.approx(-years_between(b, a), abs=1e-9)


def test_time_helpers_accept_strings():
    assert months_between("2024-03-01", "2024-01-01") == pytest.approx(60 / DAYS_PER_MONTH, abs=1e-6)


# ------------------------------------------------------------ half-life ramp
def test_half_life_fraction_key_properties():
    lag = 12.0
    assert half_life_fraction(0, lag) == pytest.approx(0.0)          # nothing at t=0
    assert half_life_fraction(lag, lag) == pytest.approx(0.5)        # half at the half-life
    assert half_life_fraction(3 * lag, lag) == pytest.approx(0.875)  # 1 - 0.5**3
    # asymptotes to 1 but never exceeds it
    assert 0.99 < float(half_life_fraction(1000, lag)) <= 1.0


def test_half_life_fraction_is_zero_before_the_event_and_monotone():
    lag = 6.0
    assert float(half_life_fraction(-1, lag)) == 0.0
    assert float(half_life_fraction(-100, lag)) == 0.0
    dt = np.arange(0, 60, 1.0)
    g = half_life_fraction(dt, lag)
    assert g.shape == dt.shape                                   # vectorized
    assert np.all(np.diff(g) >= 0)                               # never decreasing
    assert np.all((g >= 0) & (g <= 1))


def test_half_life_fraction_shorter_lag_realizes_faster():
    fast = float(half_life_fraction(6, 3.0))
    slow = float(half_life_fraction(6, 24.0))
    assert fast > slow


# ----------------------------------------------------------------------- palette
def test_palette_is_colorblind_safe_set_and_distinct():
    cycle = PALETTE.cycle
    assert len(cycle) == len(set(cycle))          # no repeated hue in a multi-series chart
    assert all(c.startswith("#") and len(c) == 7 for c in cycle)
    # the Okabe-Ito blue/orange pair is the primary contrast used across the project
    assert PALETTE.blue == "#0072B2" and PALETTE.orange == "#E69F00"
    assert set(PALETTE.as_dict()) == {"blue", "orange", "green", "vermillion",
                                      "purple", "sky", "black", "yellow"}


# -------------------------------------------------------------- series extraction
def test_observation_series_is_sorted_and_typed():
    obs = load_all(processed=True)["observations"]
    s = observation_series(obs, "ACC_OWNERSHIP")
    assert len(s) > 0
    assert s["date"].is_monotonic_increasing
    assert pd.api.types.is_datetime64_any_dtype(s["date"])
    assert pd.api.types.is_numeric_dtype(s["value"])
    assert (s["year"] == s["date"].dt.year).all()


def test_observation_series_filters_by_gender():
    obs = load_all(processed=True)["observations"]
    both = observation_series(obs, "ACC_OWNERSHIP", "all")
    female = observation_series(obs, "ACC_OWNERSHIP", "female")
    assert set(both["gender"]) == {"all"}
    assert set(female["gender"]) == {"female"}
    # unknown indicator yields an empty frame, not an error
    assert observation_series(obs, "NOT_A_CODE").empty
