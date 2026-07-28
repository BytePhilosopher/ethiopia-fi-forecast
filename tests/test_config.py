"""Tests for the typed configuration objects in src/config.py (Engineering task).

The configs are frozen dataclasses, so these tests guard two things: that they stay
immutable (a mutated singleton would silently change every downstream figure), and that
the assumptions they encode remain internally consistent with each other.
"""
import dataclasses

import pytest

from src.config import EDA_CFG, FORECAST_CFG, IMPACT_CFG, ForecastConfig, Scenario
from src.load_data import load_all


# ---------------------------------------------------------------- immutability
@pytest.mark.parametrize("cfg,field_name,value", [
    (FORECAST_CFG, "ownership_anchor", 99.0),
    (IMPACT_CFG, "key_indicators", ()),
    (EDA_CFG, "adult_population", 1.0),
])
def test_configs_are_frozen(cfg, field_name, value):
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(cfg, field_name, value)


# ------------------------------------------------------------- forecast config
def test_propensity_derives_from_the_anchors():
    # 21% pay digitally of 49% who own an account -> the 2024 propensity
    assert FORECAST_CFG.base_propensity_2024 == pytest.approx(21 / 49, abs=1e-9)
    assert 0 < FORECAST_CFG.base_propensity_2024 < 1


def test_scenarios_are_ordered_pessimistic_to_optimistic():
    s = FORECAST_CFG.ownership_scenarios
    assert set(s) == {"pessimistic", "base", "optimistic"}
    drifts = [s[k].organic_drift_pp_per_year for k in ("pessimistic", "base", "optimistic")]
    alphas = [s[k].event_attenuation for k in ("pessimistic", "base", "optimistic")]
    assert drifts == sorted(drifts)
    assert alphas == sorted(alphas)
    # attenuation is a realized *fraction* of the imported impact
    assert all(0 < a <= 1 for a in alphas)
    # the base case uses the attenuation validated in Task 3
    assert s["base"].event_attenuation == pytest.approx(0.18)


def test_digital_pay_propensity_covers_every_scenario_and_year():
    prop = FORECAST_CFG.digital_pay_propensity
    assert set(prop) == set(FORECAST_CFG.ownership_scenarios)
    for name, by_year in prop.items():
        assert set(by_year) == set(FORECAST_CFG.forecast_years), name
        assert all(0 < v < 1 for v in by_year.values()), name
        # propensity is non-decreasing over the horizon in every scenario
        vals = [by_year[y] for y in sorted(by_year)]
        assert vals == sorted(vals), name


def test_targets_are_above_the_anchor():
    # both policy targets must be aspirational relative to the 2024 observed value
    assert FORECAST_CFG.nfis_target > FORECAST_CFG.consortium_target > FORECAST_CFG.ownership_anchor
    assert 0 < FORECAST_CFG.prediction_interval < 1


def test_config_is_constructible_with_overrides():
    """A dataclass config can be varied for sensitivity analysis without touching globals."""
    alt = dataclasses.replace(ForecastConfig(), ownership_anchor=55.0)
    assert alt.ownership_anchor == 55.0
    assert FORECAST_CFG.ownership_anchor == 49.0        # the singleton is untouched
    assert alt.base_propensity_2024 == pytest.approx(21 / 55)


# --------------------------------------------------------------- impact config
def test_value_type_families_are_disjoint():
    """A value_type must combine either additively or multiplicatively, never both."""
    assert not (IMPACT_CFG.additive_types & IMPACT_CFG.multiplicative_types)


def test_magnitude_and_direction_maps_cover_the_dataset():
    """Every magnitude/direction label present in the data must have an encoding."""
    links = load_all(processed=True)["impact_links"]
    magnitudes = set(links["impact_magnitude"].dropna())
    directions = set(links["impact_direction"].dropna())
    assert magnitudes <= set(IMPACT_CFG.magnitude_ordinal)
    assert magnitudes <= set(IMPACT_CFG.magnitude_default)
    assert directions <= set(IMPACT_CFG.direction_sign)


def test_magnitude_bands_are_monotonically_ranked():
    order = ["negligible", "low", "medium", "high"]
    ordinals = [IMPACT_CFG.magnitude_ordinal[k] for k in order]
    defaults = [IMPACT_CFG.magnitude_default[k] for k in order]
    assert ordinals == sorted(ordinals)
    assert defaults == sorted(defaults)
    assert IMPACT_CFG.direction_sign["increase"] == 1
    assert IMPACT_CFG.direction_sign["decrease"] == -1


def test_key_indicators_are_unique_and_real_codes():
    codes = IMPACT_CFG.key_indicators
    assert len(codes) == len(set(codes))
    known = set(load_all(processed=True)["unified"]["indicator_code"].dropna())
    assert set(codes) <= known


# -------------------------------------------------------------------- eda config
def test_adult_population_is_a_plausible_headcount():
    # Ethiopia adults 15+: tens of millions, not a percentage and not the full population
    assert 40e6 < EDA_CFG.adult_population < 100e6
    assert EDA_CFG.figure_dpi >= EDA_CFG.screen_dpi
