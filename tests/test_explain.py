"""Tests for the explainability layer in src/explain.py (Engineering task).

The property that matters most for an explanation is *faithfulness*: the attribution must
reconstruct the number the forecast engine actually produces, and the SHAP values must
satisfy their additivity guarantee against the surrogate's own predictions. Both are
asserted here rather than merely eyeballed in a chart.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from src import explain as ex
from src import forecast as fc
from src import impact_model as im
from src.config import FORECAST_CFG, IMPACT_CFG


# ================================================== exact additive attribution
@pytest.mark.parametrize("scenario", ["pessimistic", "base", "optimistic"])
def test_contributions_sum_to_the_actual_forecast(scenario):
    """The waterfall must reconstruct the forecast engine's own 2027 number.

    This is the faithfulness check: attribution is computed independently of
    forecast.ownership_scenarios(), so agreement means the explanation describes the
    real model, not a re-implementation that has drifted from it.
    """
    year = FORECAST_CFG.forecast_years[-1]
    contrib = ex.ownership_contributions(scenario, year)
    engine = float(fc.ownership_scenarios().loc[year, scenario])

    assert contrib["pp"].sum() == pytest.approx(engine, abs=0.01)
    assert float(contrib["forecast_total"].iloc[0]) == pytest.approx(engine, abs=0.01)


def test_contributions_have_one_anchor_and_one_organic_row():
    contrib = ex.ownership_contributions("base")
    kinds = contrib["kind"].value_counts()
    assert kinds["anchor"] == 1
    assert kinds["organic"] == 1
    assert kinds["event"] >= 1
    anchor = contrib[contrib["kind"] == "anchor"]["pp"].iloc[0]
    assert anchor == pytest.approx(FORECAST_CFG.ownership_anchor)


def test_anchor_dominates_and_events_are_small():
    """The +3pp paradox, stated as a test: cataloged events explain little of the level."""
    contrib = ex.ownership_contributions("base")
    total = float(contrib["forecast_total"].iloc[0])
    events = contrib[contrib["kind"] == "event"]["pp"].sum()
    assert contrib[contrib["kind"] == "anchor"]["pp"].iloc[0] / total > 0.8
    assert 0 <= events < 10        # a few points, not the bulk of the forecast


def test_attenuation_scales_the_event_contributions():
    """Event pp must scale with α, while the anchor stays fixed."""
    base = ex.ownership_contributions("base")
    optimistic = ex.ownership_contributions("optimistic")
    a_base = FORECAST_CFG.ownership_scenarios["base"].event_attenuation
    a_opt = FORECAST_CFG.ownership_scenarios["optimistic"].event_attenuation

    ev_base = base[base["kind"] == "event"]["pp"].sum()
    ev_opt = optimistic[optimistic["kind"] == "event"]["pp"].sum()
    assert ev_opt == pytest.approx(ev_base * a_opt / a_base, rel=1e-6)
    assert (base[base["kind"] == "anchor"]["pp"].iloc[0]
            == optimistic[optimistic["kind"] == "anchor"]["pp"].iloc[0])


def test_later_years_accumulate_more_effect():
    early = ex.ownership_contributions("base", 2025)
    late = ex.ownership_contributions("base", 2027)
    assert float(late["forecast_total"].iloc[0]) > float(early["forecast_total"].iloc[0])


def test_global_event_importance_is_ranked_by_absolute_effect():
    imp = ex.global_event_importance("base")
    assert len(imp) >= 1
    assert list(imp.columns) == ["component", "pp"]
    assert imp["pp"].abs().is_monotonic_decreasing


# ============================================================ SHAP surrogate
def test_feature_frame_is_numeric_and_aligned():
    X, y, raw = ex.build_feature_frame()
    assert len(X) == len(y) == len(raw)
    assert len(X) > 0
    assert all(np.issubdtype(dt, np.number) for dt in X.dtypes)   # SHAP needs numerics
    assert (y >= 0).all()                                         # target is a magnitude
    # the categorical features were one-hot expanded, not dropped
    assert any(c.startswith("evidence_basis_") for c in X.columns)


def test_surrogate_target_is_unit_coherent():
    """The regression target must be pp-denominated throughout.

    ``impact_estimate`` means percentage points for an additive value_type but percent
    *growth* for a count, so mixing them would let a dimensional artifact drive the
    ranking. Guards the restriction to IMPACT_CFG.additive_types.
    """
    il = im.get_impact_table()
    used = il[(~il.is_qualitative) & (il.value_type.isin(IMPACT_CFG.additive_types))]
    X, y, _ = ex.build_feature_frame()
    assert len(X) == len(used)
    # no count/currency rows leaked in
    assert set(used["value_type"]) <= IMPACT_CFG.additive_types
    assert len(used) < len(il[~il.is_qualitative])      # the filter actually excludes rows


def test_shap_values_satisfy_additivity():
    """SHAP's core guarantee: base value + Σ shap == the model's prediction."""
    values, X, model, explainer = ex.shap_explanation()
    assert values.shape == X.shape
    reconstructed = explainer.expected_value + values.sum(axis=1)
    assert np.allclose(reconstructed, model.predict(X), atol=1e-6)


def test_surrogate_is_deterministic_given_a_seed():
    a, _, _, _ = ex.shap_explanation(random_state=0)
    b, _, _, _ = ex.shap_explanation(random_state=0)
    assert np.allclose(a, b)


def test_shap_importance_is_the_shared_ranking():
    """The dashboard and report read the ranking from here, so it must be well-formed.

    Deliberately does NOT assert which feature wins: on ~13 curated rows the ordering is
    leverage-sensitive, and a test that pinned the winner would encode noise as a
    requirement. The invariants that matter are shape, sort order and completeness.
    """
    imp = ex.shap_importance()
    X, _, _ = ex.build_feature_frame()
    assert list(imp.columns) == ["feature", "mean_abs_shap"]
    assert set(imp["feature"]) == set(X.columns)          # every feature is ranked
    assert imp["mean_abs_shap"].is_monotonic_decreasing   # already sorted for display
    assert (imp["mean_abs_shap"] >= 0).all()              # mean |SHAP| cannot be negative
    assert imp["mean_abs_shap"].iloc[0] > 0               # the model learned something


def test_provenance_features_carry_real_weight():
    """`evidence_basis` must remain a non-trivial driver — the bias signal we report on.

    Asserted as 'meaningful share of total importance' rather than 'rank 1', which is the
    claim the data actually supports.
    """
    imp = ex.shap_importance()
    total = imp["mean_abs_shap"].sum()
    prov = imp[imp["feature"].str.startswith("evidence_basis_")]["mean_abs_shap"].sum()
    assert prov / total > 0.10, f"provenance share {prov / total:.2%} unexpectedly low"


def test_explainability_figures_build():
    for build in (lambda: ex.fig_attribution_waterfall("base"),
                  ex.fig_shap_global, ex.fig_shap_beeswarm):
        fig = build()
        assert fig is not None
        plt.close("all")
