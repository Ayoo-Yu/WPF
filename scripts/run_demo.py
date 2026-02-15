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
    sites = list(exp_cfg.get("sites", ["site_a", "site_b"]))
    length = int(exp_cfg.get("series_length", 240))

    dataset = build_demo_dataset(sites=sites, length=length)
    result = run_experiment(config=config, dataset=dataset)

    print("Demo finished.")
    print(f"Output dir: {result['output_dir']}")
    print("Top leaderboard rows:")
    for row in result["leaderboard"][:5]:
        print(row)


if __name__ == "__main__":
    main()
