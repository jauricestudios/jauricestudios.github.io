# B6/SCOTEX study — Methods, provenance and final audit

**Status:** v1.0 publication companion · 13 November 2026 · exploratory, retrospective predictive comparison.

This document distinguishes (a) verified findings from recovered data and executed checks, (b) conclusions from the original report, and (c) limitations that cannot be resolved from the retained files.

## Research object and estimands

The observed target is accepted downward Scottish wind Balancing Mechanism action volume aggregated by settlement date/period using mapped Scottish wind BMUs. The event label equals one when this volume is positive. It is **not** a label for B6-caused curtailment. The central question is whether including B6 `headroom = published_limit - forecast_flow` improves *predictive performance* for the same target and test observations, controlling for forecast wind, forecast demand and calendar fields. The study is not causal.

### Models and measures

All event models are logistic classifiers unless otherwise noted, and use identical 25,198 training and 6,334 later evaluation periods. Categories: settlement period, month, day of week. Continuous controls: wind and demand forecast. M0/M1: standardised linear numeric terms with one-hot calendar terms. M2/M3: cubic spline transforms for wind and demand plus a wind×demand interaction, with the same categorical terms. M3 adds standardised B6 headroom; M4 uses a B6 spline plus 10,000 MW limit-state flag. Tree cross-check uses a histogram gradient-boosting classifier, identical hyperparameters with/without headroom. See scripts for exact fitted specification. No hyperparameters were selected on untouched post-publication data.

Performance metrics: ROC AUC, average precision, Brier score, log loss. Uncertainty check: paired bootstrap resampling *calendar dates* with replacement (500 replicates), conditional on the original evaluation sample and already selected models. Adjacent dates may remain dependent; the procedure does not correct for post-evaluation model selection or regime changes.

| Model | ROC AUC | Brier | Log loss |
|---|---:|---:|---:|
| M0 original linear | 0.817084 | 0.172023 | 0.530206 |
| M1 original + B6 | 0.862204 | 0.149372 | 0.474805 |
| M2 nonlinear baseline | 0.817067 | 0.168881 | 0.508485 |
| M3 nonlinear + B6 | 0.865410 | 0.144429 | 0.456838 |
| M4 nonlinear + flexible B6 | 0.879068 | 0.135367 | 0.433439 |

**Interpretation:** M2→M3 AUC delta +0.048343; approximate paired-day 95% bootstrap range +0.026566 to +0.073333. Evaluation already inspected and gaps are substantial; do not treat this as untouched confirmation. M4 is exploratory. The original two-part expected-volume model was **not** independently rebuilt in these added benchmarks; its reported MAE 899.8→860.1 MW comes from the original notebook/report.

## Database lineage and reproducibility boundary

The recovered `gb_power_b6` PostgreSQL schema defines 22 **ordinary tables**, not views:

| Layer | Number | Examples |
|---|---:|---|
| `raw` | 5 | day-ahead constraint flow, wind forecast, demand forecast, wind BOA, wind BMU reference |
| `core` | 6 | cleaned SCOTEX, wind/demand, wind BOA, BMU reference |
| `audit` | 4 | completeness, duplicate checks, wind forecast quality |
| `mart` | 7 | B6 primary periods, Scottish BOA aggregation, full and verified-wind model mart |

These objects were seen in a **schema-only** dump: they establish structure but not data provenance of each populated row. The original raw-to-mart population SQL/scripts are missing. The scripts in this package reproduce the benchmark from a **model-ready CSV export**, not from NESO raw source files. The schema-only dump should be archived privately or as a separate provenance artifact, not mistaken for the reconstruction code.

### Row-count reconciliation

Counts returned directly by the database owner through read-only SQL:

| Table | Rows |
|---|---:|
| `raw.day_ahead_constraint_flow` | 728,529 |
| `core.scotex_day_ahead` | 64,330 |
| `core.day_ahead_demand_forecast` | 96,450 |
| `core.day_ahead_wind_forecast` | 148,489 |
| `core.wind_boa` | 664,485 |
| `mart.model_full` | 42,332 |
| `mart.model_verified_wind` | 31,532 |

The model-ready CSV reproduces 31,532 settlement-period observations with unique `(settlement_date, settlement_period)` keys and no missing predictor fields in the export. It covers 657 represented days; the split consists of 525 training days and 132 evaluation days. This verifies the export's structure, **not** the missing upstream table-creation SQL.

## Forecast timestamp tests

- `core.day_ahead_wind_forecast` contains `forecast_timestamp` (`timestamp without time zone`) and a stored day-lead field; among 148,489 source records, 131,128 have `lead_days=1`, 6,031 have `lead_days=0`, and 11,330 have negative leads, some extreme. These anomalous records were not carried into the final model sample.
- `mart.verified_day_ahead_wind` contains 31,918 rows: all 31,918 recorded forecasts precede delivery. Its one-to-one match to the modelling mart covers all 31,532 model rows with zero missing matches and zero forecast-value mismatches.
- Under the assumption that stored wind clock timestamps correspond to UTC as documented by NESO, **31,532/31,532** model rows have wind forecast timestamps no later than **18:00 Europe/London on D−1**; zero are after the threshold. This was checked after correcting for BST.
- All **31,532/31,532** model rows have demand values matching `core.day_ahead_demand_forecast` records whose `publish_datetime` is no later than that same proposed cutoff; there are zero unmatched demand source keys or duplicate demand versions under the observed join.

**Crucial caveats:** A forecast creation timestamp may predate public release. The exact parsing assumptions for wind should be recovered from upstream ingestion if possible. The B6 source itself has no per-row historic first-publication/revision timestamp, so a model meeting the wind/demand clock checks is **not** proof of a point-in-time valid B6 forecast.

## Evaluation coverage and sample selection

Full evaluation calendar: **2025-10-07 to 2026-04-23 (199 days)**. Verified-wind model: **132 days**, with **67 days absent**:

| Reason | Days | Known observations |
|---|---:|---|
| Present in `mart.model_full` but no qualifying wind forecast | 62 | 2,976 settlement periods; each has `lead_days <= 0` wind-source record(s), none `lead_days=1` |
| Absent from `mart.model_full` | 5 | See B6 source diagnosis below |

All 62 missing-wind days have wind records, but none meets the previous-day lead selection. This establishes the mechanism of the retained-data exclusion, **not why the original historical source lacks qualifying forecasts**. No later-dated wind forecasts were backfilled into the model.

Comparison in full mart, evaluation window only:

| Measure | Included (6,334 periods) | Excluded for unverified wind (2,976 periods) |
|---|---:|---:|
| Event incidence | 69.1% | 65.5% |
| Mean downward BOA | 1,549.1 MW | 1,477.0 MW |
| Mean B6 headroom | 233.5 MW | 796.6 MW |
| Negative B6 headroom incidence | 43.6% | 34.7% |

These are descriptive differences, and excluded dates may have different covariate distribution. They raise a sample-selection question; they do not establish the sign or size of a resulting performance bias. Five days missing even in `model_full` are not in this comparison.

### Five dates absent from the full model

| Delivery date | Core B6 rows | Primary B6 sample rows | Final B6 rows | Audit label |
|---|---:|---:|---:|---|
| 2025-10-26 | 50 | 50 | 0 | `complete` |
| 2026-01-23 | 0 | 0 | 0 | `missing_entire_day` |
| 2026-02-10 | 48 | 0 | 0 | `value_missing` (9/48 usable) |
| 2026-02-11 | 38 | 0 | 0 | `partial_source_day` |
| 2026-04-07 | 38 | 0 | 0 | `partial_source_day` |

The two audited autumn clock-change dates, **2024-10-27** and **2025-10-26**, each have **50** original primary-sample rows but **zero** in `mart.b6_primary_sp`. Spring clock changes **2025-03-30** and **2026-03-29** each have **46** rows in both. This strongly indicates a systematic downstream autumn-time handling issue, but not its exact SQL mechanism. Restoring 2025-10-26's B6 rows alone would not repair the verified-wind sample because that date has no qualifying verified wind forecasts.

## B6 source publication and revision uncertainty

The NESO Day Ahead Constraint Flows and Limits public CSV documents constraint group, delivery clock time, limit and forecast flow. It does **not** provide a per-observation historical first-publication timestamp or original-vs-revised value marker. The database's `ingested_at` is local ingestion, not historical publication time.

NESO described an approximate 16:30 weekday publication target in an Operational Transparency Forum discussion dated 22 April 2026. This does not verify every publication in 2024–26, particularly weekends or revisions. A candidate **18:00 D−1** decision time is therefore **not established for B6**. We are publishing a retrospective historical association and incremental-prediction comparison, with operational use as future work.

## Other important validity boundaries

- The boundary headroom metric measures forecast flow relative to published limit, not the complete network state or observed constraint breach.
- The outcome includes mapped Scottish downward wind BM actions for any cause, not specifically B6-triggered actions.
- Controls use system-wide wind rather than detailed Scottish generation and omit neighbouring boundaries, outages and other relevant drivers.
- The historical dataset includes unusually high B6 limit values (e.g. 10,000 MW), treated as an explicit diagnostic; no single monotonic risk rule applies across all states.
- Models and thresholds were evaluated repeatedly on the same later window; bootstrap intervals are conditional. A future-date frozen evaluation is required for stronger generalisation.
- The binary target is **any** downward action, even if small; it is not a defined economically material curtailment event. The volume model was less improved, and its later mean level was overpredicted.
- Public data use/attribution and licensing should be confirmed before redistributing a derived dataset, rather than assuming the source licence.

## Controlled stopping rule

Publish as a **retrospective predictive study** with these limitations. Do not reprocess uncertain forecasts or retrofit the unobserved dates merely to improve performance. A separately versioned future study can fix the DST transformation, recover release logs, rebuild raw-to-mart SQL, and test a frozen specification on unseen later data, if those tasks become worthwhile.

## References

1. NESO, [Day Ahead Constraint Flows and Limits](https://www.neso.energy/data-portal/day-ahead-constraint-flows-and-limits).
2. NESO, [Historic Day Ahead Wind Forecasts](https://www.neso.energy/data-portal/day-ahead-wind-forecast/historic_day_ahead_wind_forecasts).
3. NESO, [Wind BOA Volumes](https://www.neso.energy/data-portal/wind-bmu-boa-volumes).
4. NESO, [Day Ahead Half Hourly Demand Forecast Performance](https://www.neso.energy/data-portal/day-ahead-half-hourly-demand-forecast-performance).
5. NESO, [Operational Transparency Forum, 22 April 2026](https://www.neso.energy/document/380756/download) — stated publication target, not historical timestamps.
6. [Original full B6 report](../B6_report.pdf) — predates these final audit findings.

## Relationship to prior work (non-exhaustive)

The relationship between Scottish wind, north–south transmission capacity and balancing actions has already been examined by NESO, researchers and commercial forecasters. Relevant comparators are [NESO Scottish boundaries](https://www.neso.energy/publications/electricity-ten-year-statement-etys/electricity-transmission-network-requirements/scottish-boundaries), [Modo Energy: Modelling the Balancing Mechanism (Oct 2026)](https://docs.modoenergy.com/pages/oct-2026/uk-europe/technical/bm_technical/) and [*Investigating Wind Energy Curtailment in Scotland* (2025)](https://www.mdpi.com/1996-1073/18/11/2777). This is a positioning screen, not a comprehensive originality search or a claim to reproduce the proprietary/commercial methods. The specific independently rerun comparison here is the historical incremental value of B6 forecast headroom over specified public-data baselines for a Scottish-wind-specific downward BM event target.

## Corrections to the dated original report

See [errata to the 2 October 2026 report](errata_to_2026_report.md) for the downstream DST exclusion, retrospective forecast-timing qualification, evaluation coverage, and post-report benchmark distinctions.
