# Forecast Interpretation — Access & Usage, 2025–2027 (Task 4)

**Author:** Yostina Abera
**Engine:** [`src/forecast.py`](../src/forecast.py) · **Notebook:** [`notebooks/03_forecast.ipynb`](../notebooks/03_forecast.ipynb)
**Table:** [`data/processed/forecasts_2025_2027.csv`](../data/processed/forecasts_2025_2027.csv)
**Figures:** [`15_ownership_forecast.png`](figures/15_ownership_forecast.png) · [`16_digital_pay_forecast.png`](figures/16_digital_pay_forecast.png)

---

## 1. Targets
- **Access — Account ownership** (`ACC_OWNERSHIP`): % of adults with an account at a financial
  institution or mobile-money provider. History: 22% (2014), 35% (2017), 46% (2021), 49% (2024).
- **Usage — Digital payments** (`USG_DIGITAL_PAY`): % of adults who made or received a digital
  payment. History: a **single** Findex point, 21% (2024).

## 2. Approach (and why)
Given 4 Findex points over 13 years — with clear deceleration — no single method is trustworthy
alone, so three are combined:

| Method | Role | Caveat |
|--------|------|--------|
| **Linear trend + 95% PI** | statistical baseline | ignores saturation → over-forecasts; PI very wide (n=4) |
| **Event-augmented scenario** | central ("base") forecast | anchors on 2024, adds organic drift + attenuated Task-3 event effects |
| **Scenario band** (pess/base/opt) | structural uncertainty | assumption-driven, documented below |

Digital payments, with one point, are projected as **ownership × payment-propensity**, so they
inherit the richer ownership trajectory and only require an assumption on propensity growth.

**Scenario assumptions (ownership):** organic drift and event attenuation α —
pessimistic {0.5 pp/yr, α 0.10}, base {1.2 pp/yr, α 0.18 (Task-3 validated)}, optimistic
{2.0 pp/yr, α 0.30}. **Propensity (digital pay):** share of account-holders paying digitally
(0.43 in 2024) rising to 0.445 / 0.49 / 0.55 by 2027 across the three scenarios.

## 3. Forecast table with confidence intervals

**Account ownership (% of adults)**

| Year | Pessimistic | **Base** | Optimistic | Linear trend | Linear 95% PI |
|:----:|:-----------:|:--------:|:----------:|:------------:|:-------------:|
| 2025 | 50.0 | **51.1** | 52.5 | 54.2 | [33.4, 75.1] |
| 2026 | 50.8 | **52.8** | 55.4 | 56.9 | [34.9, 79.0] |
| 2027 | 51.5 | **54.4** | 57.9 | 59.7 | [36.3, 83.0] |

**Digital-payment usage (% of adults)**

| Year | Pessimistic | **Base** | Optimistic |
|:----:|:-----------:|:--------:|:----------:|
| 2025 | 21.7 | **23.0** | 24.7 |
| 2026 | 22.3 | **24.8** | 28.2 |
| 2027 | 22.9 | **26.6** | 31.9 |

*Two uncertainty views:* the scenario band `[pessimistic, optimistic]` is the primary
(structural) interval; the linear 95% PI is the statistical interval for ownership — its width
([36, 83] by 2027) is itself the clearest statement of how little 4 points constrain the future.

## 4. What the model predicts
- **Access keeps decelerating.** Base ownership reaches **~54% by 2027** (band 51–58%), *not* the
  ~60% a naive linear fit implies. The recent +1pp/yr regime, not the historical +2.7pp/yr, governs.
- **Usage grows faster off a low base.** Digital payments reach **~27% by 2027** (base; band
  23–32%). The **usage frontier is moving while the access frontier has largely saturated** — the
  central EDA finding, projected forward and corroborated by P2P volumes (+158% YoY).
- **The NFIS-II 70%-ownership target (2025) will be missed by a wide margin.** It needs +21pp in a
  year against ~+1pp/yr observed; even the optimistic 2027 value is ~58%.

## 5. Which events have the largest potential impact
- **On usage (largest, fastest):** interoperability — **EthioPay** instant payments and the
  **M-Pesa–EthSwitch** integration — plus the **National Digital Payments Strategy**. These raise
  payment propensity and are the main lever behind the digital-payment upside.
- **On access (smaller, slower):** **Fayda digital ID** (removes the KYC barrier) and, at long lag,
  **foreign-bank entry**. Their ownership effect is deliberately **attenuated (α≈0.18)** because
  Task-3 validation showed new rails largely digitise the already-banked rather than create new
  account-holders.
- **Downside risk:** the **Safaricom price increase** and **FX-driven data-cost** rises worsen
  affordability and could suppress the optimistic paths.

## 6. Key uncertainties (explicit limitations)
1. **Digital payments rest on one data point.** The propensity trajectory is an assumption, not a
   fit — hence the widest band and no statistical PI. This is the least reliable forecast.
2. **α is calibrated on a single 2021→2024 interval** and applied forward; if the substitution
   effect weakens (more genuinely-new users), ownership could rise faster than base.
3. **Long-lag policies aren't yet observable.** NFIS-II, foreign-bank entry, EthioPay and the
   M-Pesa–EthSwitch integration are recent/future; their real magnitudes are untested.
4. **The binding constraint is demand-side device access** (phone 41%, smartphone 40%). The
   forecasts implicitly assume gradual device-gap closure; if it stalls, even the base ownership
   path is optimistic.
5. **Flat counterfactual.** Absent cataloged events the model assumes no movement, so organic
   trends are only partly represented (via the drift term).

## 7. Bottom line
Ethiopia's inclusion story to 2027 is **"usage deepening, access plateauing."** Account ownership
drifts to the low-to-mid 50s%, short of policy targets, while digital-payment usage climbs to the
high-20s% as interoperability matures. The most reliable forecast is base-case ownership; the least
reliable is digital-payment usage. Closing the phone-ownership gap is the single change that would
most shift the access path upward.
