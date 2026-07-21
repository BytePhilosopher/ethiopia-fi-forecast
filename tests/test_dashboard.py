"""Smoke tests for the Streamlit dashboard using Streamlit's AppTest harness.

Runs the app script headlessly and asserts every page renders without raising.
"""
from pathlib import Path
import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "dashboard" / "app.py")
PAGES = ["Overview", "Trends", "Forecasts", "Inclusion Projections"]


def test_app_boots():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception


@pytest.mark.parametrize("page", PAGES)
def test_each_page_renders(page):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, f"page {page} raised"


def test_forecast_model_selector():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value("Forecasts").run()
    # find the model selector by its options rather than a brittle index
    target = next((r for r in at.radio if "Linear trend + 95% PI" in list(r.options)), None)
    assert target is not None, "model selector not found on Forecasts page"
    target.set_value("Linear trend + 95% PI").run()
    assert not at.exception
