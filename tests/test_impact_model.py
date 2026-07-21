"""Tests for the event-impact model (Task 3)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from src import impact_model as im


@pytest.fixture(scope="module")
def il():
    return im.get_impact_table()


def test_effect_fraction_shape():
    # zero before the event, 0.5 at the lag (half-life), monotone up, asymptotes to 1
    assert im.effect_fraction(-5, 12) == 0.0
    assert im.effect_fraction(0, 12) == pytest.approx(0.0, abs=1e-9)
    assert im.effect_fraction(12, 12) == pytest.approx(0.5, abs=1e-9)
    assert im.effect_fraction(24, 12) == pytest.approx(0.75, abs=1e-9)
    assert im.effect_fraction(1200, 12) == pytest.approx(1.0, abs=1e-3)


def test_impact_table_units_and_flags(il):
    row = il[il.related_indicator == "ACC_OWNERSHIP"].iloc[0]
    assert row["combine"] == "additive"                       # percentage -> additive
    cnt = il[il.related_indicator == "USG_P2P_COUNT"].iloc[0]
    assert cnt["combine"] == "multiplicative"                 # count -> multiplicative
    # the three estimate-less links are flagged qualitative
    assert il["is_qualitative"].sum() >= 3
    assert il[il.is_creation]["combine"].eq("multiplicative").all()


def test_association_matrix_values(il):
    num, ordv = im.build_association_matrix(il)
    assert num.loc["Telebirr Launch", "ACC_OWNERSHIP"] == 15
    assert num.loc["M-Pesa Ethiopia Launch", "ACC_MM_ACCOUNT"] == 5
    assert num.loc["Fayda Digital ID Program Rollout", "GEN_GAP_ACC"] == -5  # decrease -> negative
    assert ordv.abs().max().max() <= 3


def test_validation_directions(il):
    res = im.validate(il)
    # MM account model is well-calibrated; ownership naive over-predicts and needs alpha<1
    mm = res["ACC_MM_ACCOUNT"]
    own = res["ACC_OWNERSHIP"]
    mm_pred = list(mm["predicted_naive"].values())[-1]
    assert 8.0 <= mm_pred <= 10.0                             # ~8.9 vs observed 9.45
    own_pred = list(own["predicted_naive"].values())[-1]
    assert own_pred > 55                                      # naive over-predicts (~62.7)
    assert 0 < own["attenuation"] < 0.5                       # strong shrinkage (~0.18)
    assert list(own["predicted_refined"].values())[-1] == pytest.approx(49.0, abs=0.5)


def test_qualitative_excluded_from_simulation(il):
    # ACC_MM_ACCOUNT has a qualitative directive link; excluding it keeps the prediction sane
    pred = im.simulate_indicator("ACC_MM_ACCOUNT", ["2024-11-29"], 4.7, "2021-12-31", il=il)
    assert 8.0 <= pred.iloc[0] <= 10.0


def test_figures_build(il):
    for f in (im.fig_effect_curves(), im.fig_association_matrix(il), im.fig_validation(il)):
        assert f is not None
        plt.close(f)
