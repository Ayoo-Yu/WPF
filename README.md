# Wind Power Forecast Racecourse (Demo)

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements-min.txt
```

For model-zoo runs (LGBM/XGBoost/RF/MLP):

```bash
pip install -r requirements-modelzoo.txt
```

2. Run demo:

```bash
python3 scripts/run_demo.py --config configs/experiments/demo.yaml
```

Run with real test CSV:

```bash
python3 scripts/run_demo.py --config configs/experiments/real_data_demo.yaml
```

Run model zoo (LGBM/XGBoost/RF/MLP + baselines):

```bash
python3 scripts/run_demo.py --config configs/experiments/model_zoo_demo.yaml
```

Quick smoke run for model zoo:

```bash
python3 scripts/run_demo.py --config configs/experiments/model_zoo_smoke.yaml
```

Random-search model zoo (fixed trial budget):

```bash
python3 scripts/run_demo.py --config configs/experiments/model_zoo_random.yaml
```

Run core unit tests:

```bash
python3 -m unittest discover -s tests -p '*_unittest.py' -v
```

3. Check outputs:

- `outputs/runs/<experiment>_<timestamp>/predictions.csv`
- `outputs/runs/<experiment>_<timestamp>/metrics.csv`
- `outputs/runs/<experiment>_<timestamp>/leaderboard.csv`
- `outputs/runs/<experiment>_<timestamp>/run_summary.json`
- `outputs/runs/<experiment>_<timestamp>/dataset_profile.json`

## Web Dashboard

1. Start dashboard server:

```bash
python3 scripts/dashboard_server.py
```

2. Open in browser:

```text
http://127.0.0.1:8000
```

3. In the page:

- Run demo from UI
- Browse historical runs
- Filter by site
- Switch leaderboard metric (`avg_MAE` / `avg_RMSE` / `avg_nMAE`)
- View dataset quality snapshot (aligned rows, time range, target stats)
- View leaderboard and metrics table
- View charts (avg_MAE bar, MAE/RMSE vs horizon lines)
- Metrics support segment filtering (`overall` / `season` / `wind_bin`)
- Multi-page workspace:
  - `赛马场`: ranking/metrics/charts
  - `实验中心`: configs list, preview, quick-launch
  - `报告中心`: run summary, `report.md`, artifacts list
  - `报告中心` supports run comparison and file download (`report.md`, leaderboard.csv, metrics.csv)
  - `报告中心` includes best-model trend and segment-level run comparison
  - `实验中心` includes storage summary and old-run cleanup (with dry-run preview)

## What This Demo Includes

- Config-driven experiment definition
- Unified model interface (`ForecastModel`)
- Model variants via `params_grid`
- Four baseline/benchmark models (`persistence`, `moving_average`, `linear_ar`, `linear_exog`)
- Extra model plugins (`lightgbm`, `xgboost`, `random_forest`, `mlp`)
- Multi-site and multi-horizon backtest
- MAE/RMSE/nMAE evaluation and leaderboard generation
- Segmented evaluation in metrics (`segment_key`, `segment_value`)
- Stability leaderboard output (`stability_leaderboard.csv`)
- Optional `experiment.refit_each_origin` to control rolling refit behavior
- Optional `experiment.skip_failed_models` to skip dependency/model failures
- Parallel trial execution via `experiment.max_workers`
  - Optional `experiment.model_type_limits` for model-category throttling (`boost`/`forest`/`nn`/`linear`/`baseline`)
- Supports search mode in model config:
  - `search.method: grid|random`
  - `search.max_trials: <int>`
  - experiment-level `search_seed`

## Real CSV Notes

- `data.feature_cols` can be used to select NWP features for exogenous models.
- `linear_exog` consumes both target lags and selected NWP features.

## Dependency Notes

- `requirements-min.txt`: minimal set for baseline/demo pipeline.
- `requirements-modelzoo.txt`: includes tree/NN model dependencies.

When `skip_failed_models: true`, missing models are recorded in:

- `outputs/runs/<run_id>/failed_models.json`
- `outputs/runs/<run_id>/run_summary.json` (`failed_models` field)

Each run now also generates:

- `outputs/runs/<run_id>/report.md` (leaderboard + segment summary + failures)
- `outputs/runs/<run_id>/stability_leaderboard.csv`

## CI

- GitHub Actions workflow: `.github/workflows/ci.yml`
- Runs `unittest` suite on push/pull request.
