"""Pure (Streamlit-free) data helpers for the dashboard — unit-testable.

Everything the dashboard needs to read/compute lives here so app.py stays a thin UI layer
and the logic can be tested without spinning up Streamlit.
"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.load_data import load_all  # noqa: E402
from src.utils import PALETTE, observation_series  # noqa: E402
from src.config import FORECAST_CFG  # noqa: E402

# Okabe-Ito colorblind-safe palette — single source of truth in src/utils.
OI = PALETTE.as_dict()
INK, MUTED, GRID = PALETTE.ink, PALETTE.muted, PALETTE.grid

CONSORTIUM_TARGET = FORECAST_CFG.consortium_target  # % account-ownership inclusion target

INDICATOR_LABELS = {
    "ACC_OWNERSHIP": "Account ownership (%)",
    "ACC_MM_ACCOUNT": "Mobile-money account (%)",
    "USG_DIGITAL_PAY": "Digital-payment usage (%)",
    "ACC_4G_COV": "4G coverage (%)",
    "ACC_PHONE_OWN": "Phone ownership (%)",
    "ACC_SMARTPHONE": "Smartphone adoption (%)",
    "USG_P2P_COUNT": "P2P transactions (count)",
    "USG_ATM_COUNT": "ATM transactions (count)",
    "USG_TELEBIRR_USERS": "Telebirr users",
    "USG_MPESA_USERS": "M-Pesa users",
    "GEN_GAP_ACC": "Gender gap, ownership (pp)",
}


def load_observations() -> pd.DataFrame:
    d = load_all(processed=True)
    o = d["observations"].copy()
    o["date"] = pd.to_datetime(o["observation_date"])
    o["year"] = o["date"].dt.year
    o["value"] = pd.to_numeric(o["value_numeric"], errors="coerce")
    return o


def get_series(obs: pd.DataFrame, code: str, gender: str = "all") -> pd.DataFrame:
    s = observation_series(obs, code, gender)
    return s[["date", "year", "value", "unit", "source_name", "confidence"]]


def _latest(obs: pd.DataFrame, code: str, gender: str = "all") -> pd.Series | None:
    s = get_series(obs, code, gender)
    return None if s.empty else s.iloc[-1]


def key_metrics(obs: pd.DataFrame) -> list[dict]:
    """Summary cards: current value + delta vs previous observation where available."""
    cards = []

    def card(code: str, label: str, fmt: str = "{:.1f}%", scale: float = 1.0,
             delta_suffix: str = "pp") -> None:
        s = get_series(obs, code)
        if s.empty:
            return
        cur = s.iloc[-1]["value"]
        delta = None
        if len(s) >= 2:
            delta = cur - s.iloc[-2]["value"]
        cards.append({
            "label": label,
            "value": fmt.format(cur / scale),
            "delta": None if delta is None else f"{delta/scale:+.1f} {delta_suffix}",
            "year": int(s.iloc[-1]["year"]),
        })

    card("ACC_OWNERSHIP", "Account ownership")
    card("USG_DIGITAL_PAY", "Digital-payment usage")
    card("ACC_MM_ACCOUNT", "Mobile-money account")
    card("USG_TELEBIRR_USERS", "Telebirr users", fmt="{:.1f}M", scale=1e6, delta_suffix="M")
    card("USG_MPESA_USERS", "M-Pesa users", fmt="{:.1f}M", scale=1e6, delta_suffix="M")
    card("GEN_GAP_ACC", "Gender gap (ownership)", fmt="{:.0f} pp", delta_suffix="pp")
    return cards


def crossover_ratio(obs: pd.DataFrame) -> tuple[float | None, int | None]:
    """P2P/ATM transaction-count crossover ratio (>1 => digital P2P exceeds ATM)."""
    r = _latest(obs, "USG_CROSSOVER")
    if r is not None:
        return float(r["value"]), int(r["year"])
    p2p, atm = _latest(obs, "USG_P2P_COUNT"), _latest(obs, "USG_ATM_COUNT")
    if p2p is not None and atm is not None and atm["value"]:
        return float(p2p["value"] / atm["value"]), int(p2p["year"])
    return None, None


def growth_rates(obs: pd.DataFrame) -> pd.DataFrame:
    """Account-ownership pp gain per inter-survey period (annualized)."""
    s = get_series(obs, "ACC_OWNERSHIP").reset_index(drop=True)
    rows = []
    for i in range(1, len(s)):
        y0, y1 = s["year"][i - 1], s["year"][i]
        v0, v1 = s["value"][i - 1], s["value"][i]
        rows.append({"period": f"{y0}–{y1}", "pp_total": v1 - v0,
                     "pp_per_year": (v1 - v0) / (y1 - y0)})
    return pd.DataFrame(rows)


def download_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
