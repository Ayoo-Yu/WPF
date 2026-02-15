# Wind Power Forecast Racecourse (Demo)

## Quick Start

1. Install dependency:

```bash
pip install pyyaml
```

2. Run demo:

```bash
python3 scripts/run_demo.py --config configs/experiments/demo.yaml
```

3. Check outputs:

- `outputs/runs/<experiment>_<timestamp>/predictions.csv`
- `outputs/runs/<experiment>_<timestamp>/metrics.csv`
- `outputs/runs/<experiment>_<timestamp>/leaderboard.csv`
- `outputs/runs/<experiment>_<timestamp>/run_summary.json`

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
- View leaderboard and metrics table
- View charts (avg_MAE bar, MAE/RMSE vs horizon lines)

## What This Demo Includes

- Config-driven experiment definition
- Unified model interface (`ForecastModel`)
- Two baseline models (`persistence`, `moving_average`)
- Multi-site and multi-horizon backtest
- MAE/RMSE evaluation and leaderboard generation
