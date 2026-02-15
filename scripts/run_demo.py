from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.orchestrator import run_experiment
from src.data.csv_loader import CSVLoadResult, load_scada_nwp_series
from src.utils.io import read_yaml


def generate_site_series(length: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    series: list[float] = []
    for t in range(length):
        seasonal = 0.5 + 0.35 * math.sin(2 * math.pi * (t % 24) / 24)
        trend = 0.0008 * t
        noise = rng.uniform(-0.06, 0.06)
        value = max(0.0, min(1.0, seasonal + trend + noise))
        series.append(round(value, 6))
    return series


def build_demo_dataset(sites: list[str], length: int) -> dict[str, list[float]]:
    return {
        site_id: generate_site_series(length=length, seed=1000 + i * 17)
        for i, site_id in enumerate(sites)
    }


def _load_real_dataset(config: dict) -> tuple[dict, dict]:
    exp_cfg = config.get("experiment", {})
    data_cfg = config.get("data", {})
    scada_csv = data_cfg.get("scada_csv")
    nwp_csv = data_cfg.get("nwp_csv")
    if not scada_csv or not nwp_csv:
        raise ValueError("For real_csv mode, both data.scada_csv and data.nwp_csv are required")

    site_id = str(exp_cfg.get("sites", ["site_real_01"])[0])
    target_col = str(data_cfg.get("target_col", "Total_Power"))
    timestamp_col = str(data_cfg.get("timestamp_col", "Timestamp"))
    max_rows = data_cfg.get("max_rows")
    max_rows_int = int(max_rows) if max_rows is not None else None

    result: CSVLoadResult = load_scada_nwp_series(
        scada_csv=scada_csv,
        nwp_csv=nwp_csv,
        site_id=site_id,
        target_col=target_col,
        timestamp_col=timestamp_col,
        max_rows=max_rows_int,
    )
    feature_cols = data_cfg.get("feature_cols")
    if feature_cols:
        wanted = [str(c) for c in feature_cols]
        filtered_exog = [{k: v for k, v in row.items() if k in wanted} for row in result.exog_rows]
    else:
        filtered_exog = result.exog_rows

    stats = dict(result.stats)
    if filtered_exog and feature_cols:
        stats["n_exog_features"] = len(filtered_exog[0].keys())
        stats["feature_cols"] = ",".join(sorted(filtered_exog[0].keys()))

    payload = {
        site_id: {
            "series": result.series,
            "exog": filtered_exog,
            "timestamps": result.timestamps,
        }
    }
    return payload, stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Run wind power racecourse demo")
    parser.add_argument(
        "--config",
        default="configs/experiments/demo.yaml",
        help="Path to YAML experiment config",
    )
    args = parser.parse_args()

    config = read_yaml(args.config)
    exp_cfg = config.get("experiment", {})
    data_source = str(exp_cfg.get("data_source", "synthetic"))

    dataset_stats: dict = {}
    if data_source == "real_csv":
        dataset, dataset_stats = _load_real_dataset(config)
    else:
        sites = list(exp_cfg.get("sites", ["site_a", "site_b"]))
        length = int(exp_cfg.get("series_length", 240))
        dataset = build_demo_dataset(sites=sites, length=length)
        dataset_stats = {
            "source": "synthetic",
            "sites": ",".join(sites),
            "series_length": length,
        }

    result = run_experiment(config=config, dataset=dataset, dataset_stats=dataset_stats)

    print("Demo finished.")
    print(f"Output dir: {result['output_dir']}")
    print("Top leaderboard rows:")
    for row in result["leaderboard"][:5]:
        print(row)


if __name__ == "__main__":
    main()
