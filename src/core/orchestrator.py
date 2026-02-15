from __future__ import annotations

from datetime import datetime

from src.core.evaluator import evaluate
from src.core.leaderboard import build_leaderboard
from src.core.runner import run_backtest
from src.data.dataset_registry import DatasetRegistry
from src.models.registry import create_model
from src.utils.io import write_csv, write_json
from src.utils.logger import get_logger


def run_experiment(config: dict, dataset: dict[str, list[float]]) -> dict:
    logger = get_logger("wpf.orchestrator")

    exp_cfg = config.get("experiment", {})
    models_cfg = config.get("models", [])

    exp_name = exp_cfg.get("name", "demo_experiment")
    dataset_version = exp_cfg.get("dataset_version", "demo_dataset_v1")
    train_size = int(exp_cfg.get("train_size", 120))
    horizons = list(exp_cfg.get("horizons", [1, 2, 4]))
    sites = list(exp_cfg.get("sites", list(dataset.keys())))

    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"outputs/runs/{exp_name}_{run_tag}"

    logger.info("Experiment=%s, sites=%s", exp_name, sites)

    all_preds: list[dict] = []
    for model_cfg in models_cfg:
        model_name = model_cfg["name"]
        params = model_cfg.get("params", {})
        model = create_model(model_name, params=params)

        for site_id in sites:
            series = dataset[site_id]
            preds = run_backtest(
                series=series,
                site_id=site_id,
                model=model,
                horizons=horizons,
                train_size=train_size,
            )
            all_preds.extend(preds)

    metric_rows = evaluate(all_preds)
    leaderboard = build_leaderboard(metric_rows)

    write_csv(f"{out_dir}/predictions.csv", all_preds)
    write_csv(f"{out_dir}/metrics.csv", metric_rows)
    write_csv(f"{out_dir}/leaderboard.csv", leaderboard)
    write_json(
        f"{out_dir}/run_summary.json",
        {
            "experiment": exp_name,
            "dataset_version": dataset_version,
            "horizons": horizons,
            "sites": sites,
            "models": [m["name"] for m in models_cfg],
            "output_dir": out_dir,
        },
    )

    if dataset:
        first_site = sites[0]
        registry = DatasetRegistry()
        registry.register(
            dataset_version_id=dataset_version,
            site_ids=sites,
            time_start="t0",
            time_end=f"t{len(dataset[first_site]) - 1}",
            notes="demo synthetic data",
        )

    logger.info("Run completed. Output=%s", out_dir)
    return {
        "output_dir": out_dir,
        "leaderboard": leaderboard,
        "metrics": metric_rows,
    }
