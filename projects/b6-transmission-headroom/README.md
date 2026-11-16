# B6 — Reproducible exploratory event-model benchmarks

This folder supports the portfolio note [B6 Transmission Headroom & Scottish Wind Balancing](../b6-transmission-headroom.md).

**Status:** retrospective, exploratory benchmark. It does not establish the historical availability of each B6 observation at a fixed forecast cutoff.

## Contents

| Path | Contents |
|---|---|
| `data/b6_model_benchmark.csv` | **Not redistributed in this public patch.** Place your locally held, model-ready 31,532-row export at this path before running the scripts. |
| `scripts/b6_benchmark_reanalysis.py` | Reproduces M0–M4 classification models, bootstrap and wind strata |
| `scripts/b6_tree_robustness.py` | Runs tree-based comparison and monthly diagnostic |
| `scripts/verify_model_export.py` | Read-only row-count, key, target and split consistency check |
| `results/` | Summary metrics and diagnostics; row-level model prediction files are not distributed by default |
| `docs/methods_and_audit.md` | Source-lineage, timing, missing-day, DST and interpretation audit |

This package **cannot** rebuild the PostgreSQL marts from raw NESO source downloads: the original data-population SQL is unavailable. The older `01_b6_analysis.ipynb` and `B6_report.pdf` already in this project folder document the original two-part event/volume approach, but they predate the final audit disclosures.

## Reproduce

From a local terminal at the root of this folder, first place your separately retained 31,532-row export at `data/b6_model_benchmark.csv`. The input data are **not** in this public patch. Then run:

```bash
python -m pip install -r requirements.txt
python scripts/verify_model_export.py
python scripts/b6_benchmark_reanalysis.py
python scripts/b6_tree_robustness.py
```

The scripts read a local CSV and write `results/`; they do not access or modify PostgreSQL. They require running the main benchmark before the tree script because the latter reads the main predictions file for monthly diagnostics. The model code uses a fixed random seed for resampling and explicit training-date split selection.

Environment used for the saved verification: Python 3, NumPy 2.3.5, pandas 2.2.3, scikit-learn 1.8.0. Other compatible versions may produce small numeric changes.

## Model definitions and reported scores

| Model | ROC AUC | Brier |
|---|---:|---:|
| M0 original controls | 0.8171 | 0.1720 |
| M1 original controls + B6 | 0.8622 | 0.1494 |
| M2 nonlinear controls | 0.8171 | 0.1689 |
| M3 nonlinear + B6 | 0.8654 | 0.1444 |
| M4 nonlinear + flexible B6 | 0.8791 | 0.1354 |

All results use the previously examined 2025-10-07–2026-04-23 evaluation sample (6,334 periods on 132 observed dates). The full calendar span contains 199 dates. AUC improvement is not proof of a causal mechanism, a verified 18:00 D−1 operational forecast or performance on missing days.

For the full evidence qualification, consult [`docs/methods_and_audit.md`](docs/methods_and_audit.md).

**Data licensing:** Check the terms for each redistributed source and attribution before publishing the model-ready export. If uncertain, keep the CSV in a private archive and publish the code, provenance documentation and aggregate metrics, with instructions for accessing the source data; results reproduction then requires the separately supplied derived export.

**Publication default:** Only the aggregate model metrics and diagnostic summary files are included. The full model-ready export, row-level prediction files and schema-only dump remain in the separate private review archive. The scripts will generate row-level prediction files locally if an eligible CSV is present; do not commit them without a separate disclosure/licence review.
