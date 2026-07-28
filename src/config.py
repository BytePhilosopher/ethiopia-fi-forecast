"""Typed configuration objects for the modelling code.

Replaces scattered module-level dicts and magic numbers with dataclasses that document
intent and units in one place. Modules import the singletons (``IMPACT_CFG``,
``FORECAST_CFG``) rather than redefining literals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

import pandas as pd

# --------------------------------------------------------------- impact model
@dataclass(frozen=True)
class ImpactConfig:
    """Constants for translating impact_link records into effects over time."""

    # qualitative magnitude band -> ordinal strength (unit-free, for the colour scale)
    magnitude_ordinal: dict[str, float] = field(default_factory=lambda: {
        "high": 3.0, "medium": 2.0, "low": 1.0, "negligible": 0.5})
    # fallback asymptote when a numeric estimate is missing (band midpoints)
    magnitude_default: dict[str, float] = field(default_factory=lambda: {
        "high": 20.0, "medium": 10.0, "low": 3.0, "negligible": 0.5})
    direction_sign: dict[str, int] = field(default_factory=lambda: {
        "increase": 1, "decrease": -1, "stabilize": 0, "mixed": 0})
    # indicator value_type -> how effects combine
    additive_types: frozenset[str] = frozenset({"percentage", "gap_pp"})
    multiplicative_types: frozenset[str] = frozenset(
        {"count", "currency_etb", "currency_usd", "ratio"})
    # key indicators used as association-matrix columns (task-specified + high-value)
    key_indicators: tuple[str, ...] = (
        "ACC_OWNERSHIP", "ACC_MM_ACCOUNT", "ACC_4G_COV", "USG_DIGITAL_PAY",
        "USG_P2P_COUNT", "USG_TELEBIRR_USERS", "USG_MPESA_USERS", "USG_MPESA_ACTIVE",
        "AFF_DATA_INCOME", "GEN_GAP_ACC", "GEN_MM_SHARE", "DEP_BORROWED")


@dataclass(frozen=True)
class Scenario:
    """One forecast scenario for account ownership."""

    organic_drift_pp_per_year: float   # non-event trend
    event_attenuation: float           # realized fraction of imported ownership impacts (α)


@dataclass(frozen=True)
class ForecastConfig:
    """Constants and scenario assumptions for the 2025-2027 forecast."""

    forecast_years: tuple[int, ...] = (2025, 2026, 2027)
    anchor_date: pd.Timestamp = field(default_factory=lambda: pd.Timestamp("2024-11-29"))
    ownership_anchor: float = 49.0          # % adults, Findex 2024
    digital_pay_anchor: float = 21.0        # % adults, Findex 2024
    nfis_target: float = 70.0               # NFIS-II ownership target
    consortium_target: float = 60.0         # consortium inclusion target
    prediction_interval: float = 0.95

    ownership_scenarios: dict[str, Scenario] = field(default_factory=lambda: {
        "pessimistic": Scenario(0.5, 0.10),
        "base": Scenario(1.2, 0.18),         # α = the Task-3 validated value
        "optimistic": Scenario(2.0, 0.30)})
    # share of account-holders paying digitally, per scenario & year
    digital_pay_propensity: dict[str, dict[int, float]] = field(default_factory=lambda: {
        "pessimistic": {2025: 0.435, 2026: 0.440, 2027: 0.445},
        "base": {2025: 0.450, 2026: 0.470, 2027: 0.490},
        "optimistic": {2025: 0.470, 2026: 0.510, 2027: 0.550}})

    @property
    def base_propensity_2024(self) -> float:
        return self.digital_pay_anchor / self.ownership_anchor


# --------------------------------------------------------------------- figures
@dataclass(frozen=True)
class EdaConfig:
    """Constants used by the EDA figure engine.

    Collected here so the numbers that appear in chart annotations are stated once,
    with their provenance, instead of sitting inline as bare literals.
    """

    # Adults 15+ in Ethiopia: World Bank population ~126M x ~55% aged 15+.
    # Used only to convert a survey ownership *rate* into an absolute headcount
    # for the registered-vs-active comparison bar.
    adult_population: float = 70e6
    figure_dpi: int = 150           # dpi for saved PNGs
    screen_dpi: int = 110           # dpi for on-screen/notebook rendering
    heatmap_empty_color: str = "#f5f5f5"   # missing cells: light gray, never dark


IMPACT_CFG: Final[ImpactConfig] = ImpactConfig()
FORECAST_CFG: Final[ForecastConfig] = ForecastConfig()
EDA_CFG: Final[EdaConfig] = EdaConfig()
