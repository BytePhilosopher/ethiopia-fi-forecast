"""Shared, dependency-light utilities used across the analysis modules.

Consolidates logic that was previously duplicated (the colorblind-safe palette, the
month-difference helper, and single-indicator series extraction) so there is one source
of truth. Kept import-light (numpy/pandas only) so any module can use it.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Final, TypeAlias, Union

import numpy as np
import pandas as pd

# Anything pandas can coerce to a timestamp — ISO strings are used throughout the code.
DateLike: TypeAlias = Union[str, date, datetime, pd.Timestamp]
# A scalar or an array of them; the half-life ramp is vectorized over both.
ArrayLike: TypeAlias = Union[float, int, Sequence[float], np.ndarray, pd.Series]

# --- time -------------------------------------------------------------------
DAYS_PER_MONTH: Final[float] = 30.44
DAYS_PER_YEAR: Final[float] = 365.25


def months_between(t: DateLike, t0: DateLike) -> float:
    """Whole-and-fractional months from ``t0`` to ``t`` (negative if t < t0)."""
    return (pd.to_datetime(t) - pd.to_datetime(t0)).days / DAYS_PER_MONTH


def years_between(t: DateLike, t0: DateLike) -> float:
    """Whole-and-fractional years from ``t0`` to ``t``."""
    return (pd.to_datetime(t) - pd.to_datetime(t0)).days / DAYS_PER_YEAR


def observation_series(obs: pd.DataFrame, code: str, gender: str = "all") -> pd.DataFrame:
    """Return one indicator's observations, date-sorted, with parsed ``date``/``value``.

    ``obs`` must be the observations frame from ``load_all``. The returned frame always
    has ``date`` (datetime), ``year`` (int) and ``value`` (float) columns.
    """
    s = obs[(obs["indicator_code"] == code) & (obs["gender"] == gender)].copy()
    s["date"] = pd.to_datetime(s["observation_date"])
    s["year"] = s["date"].dt.year
    s["value"] = pd.to_numeric(s["value_numeric"], errors="coerce")
    return s.sort_values("date")


# --- palette ----------------------------------------------------------------
@dataclass(frozen=True)
class Palette:
    """Okabe-Ito colorblind-safe palette, shared by every chart in the project."""

    blue: str = "#0072B2"
    orange: str = "#E69F00"
    green: str = "#009E73"
    vermillion: str = "#D55E00"
    purple: str = "#CC79A7"
    sky: str = "#56B4E9"
    black: str = "#111111"
    yellow: str = "#F0E442"
    ink: str = "#1a1a1a"
    muted: str = "#6b6b6b"
    grid: str = "#e6e6e6"

    @property
    def cycle(self) -> list[str]:
        """Ordered hues for multi-series charts (most-distinct first)."""
        return [self.blue, self.orange, self.green, self.vermillion,
                self.purple, self.sky, self.black, self.yellow]

    def as_dict(self) -> dict[str, str]:
        return {"blue": self.blue, "orange": self.orange, "green": self.green,
                "vermillion": self.vermillion, "purple": self.purple, "sky": self.sky,
                "black": self.black, "yellow": self.yellow}


PALETTE: Final[Palette] = Palette()


def half_life_fraction(months_since_event: ArrayLike, lag_months: float) -> np.ndarray:
    """Fraction of an effect realized ``Δt`` months after an event.

    ``g(Δt) = 1 - 0.5**(Δt / lag)`` for ``Δt >= 0`` (else 0). ``lag`` is the half-life:
    ``g(lag) = 0.5``. Vectorized over ``months_since_event``.
    """
    dt = np.asarray(months_since_event, dtype=float)
    frac = 1.0 - np.power(0.5, np.clip(dt, 0, None) / lag_months)
    return np.where(dt < 0, 0.0, frac)
