"""Smoke tests: the EDA figure engine builds every figure without error."""
import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt
import pytest

from src import eda


@pytest.fixture(scope="module")
def loaded():
    return eda._load()  # (d, obs)


def test_all_figures_build(loaded):
    d, obs = loaded
    builders = [
        lambda: eda.fig_overview(d),
        lambda: eda.fig_coverage(obs)[0],
        lambda: eda.fig_access_trajectory(obs, d),
        lambda: eda.fig_growth(obs)[0],
        lambda: eda.fig_gender(obs),
        lambda: eda.fig_usage_growth(obs),
        lambda: eda.fig_registered_active(obs),
        lambda: eda.fig_p2p_atm(obs),
        lambda: eda.fig_enablers(obs),
        lambda: eda.fig_timeline(d),
        lambda: eda.fig_impact_matrix(d),
    ]
    for build in builders:
        fig = build()
        assert fig is not None
        plt.close(fig)


def test_growth_is_decelerating(loaded):
    """The headline EDA finding must hold in the data."""
    _, obs = loaded
    _, g = eda.fig_growth(obs)
    plt.close("all")
    # last inter-survey period (2021-2024) is the slowest annualized gain
    assert g["pp_per_yr"].iloc[-1] == g["pp_per_yr"].min()
    assert g["pp_total"].iloc[-1] == 3  # +3pp 2021->2024
