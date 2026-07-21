"""Tests for the 2025-2027 forecasting engine (Task 4)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest

from src import forecast as fc


def test_ownership_history_anchor():
    s = fc.ownership_series()
    assert list(s["value"]) == [22.0, 35.0, 46.0, 49.0]
    assert s["value"].iloc[-1] == fc.OWN_ANCHOR


def test_linear_trend_slope_and_interval():
    lin, params = fc.linear_trend(fc.ownership_series())
    assert params["slope"] == pytest.approx(2.71, abs=0.05)     # ~2.7 pp/yr
    # prediction interval must widen with the horizon and bracket the point estimate
    row27 = lin.set_index("year").loc[2027]
    assert row27["lo"] < row27["value"] < row27["hi"]
    assert (lin["hi"] - lin["lo"]).is_monotonic_increasing


def test_scenarios_ordered_and_decelerating():
    own = fc.ownership_scenarios()
    for yr in fc.FORECAST_YEARS:
        assert own.loc[yr, "pessimistic"] <= own.loc[yr, "base"] <= own.loc[yr, "optimistic"]
    # base stays well below the naive linear trend (captures deceleration)
    lin, _ = fc.linear_trend(fc.ownership_series())
    assert own.loc[2027, "base"] < lin.set_index("year").loc[2027, "value"]
    # and well short of the NFIS-II 70% target
    assert own.loc[2027, "optimistic"] < 70


def test_digital_pay_decomposition():
    dp = fc.digital_pay_scenarios()
    # anchored consistently: 2024 propensity * ownership reproduces ~21
    assert fc.DP_PROPENSITY_0 == pytest.approx(21 / 49, abs=1e-6)
    for yr in fc.FORECAST_YEARS:
        assert dp.loc[yr, "pessimistic"] <= dp.loc[yr, "base"] <= dp.loc[yr, "optimistic"]
    # usage grows off the low base but stays below ownership (a subset relationship)
    own = fc.ownership_scenarios()
    assert dp.loc[2027, "base"] < own.loc[2027, "base"]
    assert dp.loc[2027, "base"] > fc.DP_ANCHOR


def test_forecast_table_shape():
    t = fc.forecast_table()
    assert set(t["target"]) == {"ACC_OWNERSHIP", "USG_DIGITAL_PAY"}
    assert len(t) == 6
    assert {"base", "pessimistic", "optimistic"} <= set(t.columns)


def test_figures_build():
    for f in (fc.fig_ownership_forecast(), fc.fig_digital_pay_forecast()):
        assert f is not None
        plt.close(f)
