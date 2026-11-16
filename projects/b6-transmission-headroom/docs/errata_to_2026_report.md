# B6 — Notes on the original 2 October 2026 report

This note accompanies the original 34-page PDF. The original report is retained unchanged as a dated research record; the updated portfolio page and methods appendix take precedence on the points below.

## 1. Autumn daylight-saving settlement periods

Section 6.3 of the original report states that the final modelling mart retains valid 50-period autumn clock-change days. Subsequent PostgreSQL auditing found otherwise:

| Delivery date | Rows in initial B6 primary sample | Rows in final B6 settlement-period mart |
|---|---:|---:|
| 27 October 2024 | 50 | 0 |
| 26 October 2025 | 50 | 0 |

For comparison, 30 March 2025 and 29 March 2026 each have 46 rows in both layers. The upstream records for the autumn days were preserved, but the downstream transformation excluded them. The original SQL responsible is unavailable, so the exact mechanism has **not** been established. Do not claim the *final* mart handles autumn clock changes correctly.

## 2. Day-ahead information-set qualification

The original report describes the wind-forecast records as time-verified before delivery. Later checks established that all 31,532 final modelling rows have stored wind and matched demand forecast timestamps satisfying a **candidate 18:00 Europe/London D−1 cutoff**, subject to the wind timestamp's UTC interpretation.

However, the archived B6 forecast flows/limits **do not include original historical first-release or revision timestamps**. Consequently the study does not certify that the B6 information was available by 18:00 D−1 across the full historical evaluation. It should be presented as a *retrospective incremental-prediction study*, not a fully point-in-time validated operational forecast.

## 3. Incomplete evaluation coverage

The later evaluation covers only **132 of the 199 calendar days** from 7 October 2025 through 23 April 2026. The 67 absent dates comprise 62 dates with B6 observations but no qualifying retained previous-day wind forecast, plus five dates absent from the final B6 mart. The included and excluded periods differ in average headroom and outcome incidence. Model metrics do **not** establish the same performance on unobserved dates.

## 4. Additional benchmarks added after the report

From the frozen 31,532-row model-ready export, independent exploratory reanalysis reproduced the original M0/M1 classifier results and added nonlinear controls and a tree-based check. The nonlinear baseline ROC AUC was 0.8171 versus 0.8654 with linear B6 headroom included (M2→M3). These extra comparisons **do not independently reproduce or upgrade** the report's two-part positive-volume model.

All additional benchmarks evaluate an already examined historical period. They are not fresh untouched confirmation.

## Bottom line

The original predictive comparison remains reproducible for its *observed model-ready data*. The record above corrects overstatements about final dataset coverage, complete DST handling and operational publication timing. No causal B6-attribution, real-time trading performance or all-days forecast performance is established.
