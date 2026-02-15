from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from itertools import product
import random
import threading

from src.core.evaluator import evaluate
from src.core.leaderboard import build_leaderboard
from src.core.reporting import build_markdown_report
from src.core.runner import run_backtest
from src.core.stability import build_stability_leaderboard
from src.data.dataset_registry import DatasetRegistry
from src.models.registry import create_model
from src.utils.io import write_csv, write_json
from src.utils.logger import get_logger


def _format_model_label(name: str, params: dict) -> str:
    if not params:
        return name
    param_str = ",".join(f"{k}={params[k]}" for k in sorted(params.keys()))
    return f"{name}[{param_str}]"


def _expand_model_specs(models_cfg: list[dict]) -> list[dict]:
    return _expand_model_specs_with_seed(models_cfg=models_cfg, seed=42)


def _expand_model_specs_with_seed(models_cfg: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    expanded: list[dict] = []
    for m in models_cfg:
        name = m["name"]
        if "params_grid" in m and m["params_grid"]:
            grid: dict = m["params_grid"]
            keys = sorted(grid.keys())
            values = [list(grid[k]) for k in keys]
            all_combos = list(product(*values))
            search_cfg = m.get("search", {})
            method = str(search_cfg.get("method", "grid")).lower()
            max_trials = int(search_cfg.get("max_trials", 0))
            if method == "random":
                if max_trials <= 0:
                    max_trials = min(10, len(all_combos))
                trial_count = min(max_trials, len(all_combos))
                chosen = rng.sample(all_combos, k=trial_count)
            else:
                chosen = all_combos
                if max_trials > 0:
                    chosen = chosen[:max_trials]

            for combo in chosen:
                params = {k: v for k, v in zip(keys, combo)}
                expanded.append(
                    {
                        "name": name,
                        "params": params,
                        "label": _format_model_label(name, params),
                    }
                )
            continue

        params = dict(m.get("params", {}))
        expanded.append(
            {
                "name": name,
                "params": params,
                "label": _format_model_label(name, params),
            }
        )
    return expanded


def _run_single_task(task: dict) -> dict:
    model_name = task["model_name"]
    params = task["params"]
    model_label = task["model_label"]
    site_id = task["site_id"]
    series = task["series"]
    exog_rows = task.get("exog_rows")
    timestamps = task.get("timestamps")
    horizons = task["horizons"]
    train_size = task["train_size"]
    refit_each_origin = task["refit_each_origin"]

    model = create_model(model_name, params=params)
    preds = run_backtest(
        series=series,
        site_id=site_id,
        model=model,
        model_label=model_label,
        horizons=horizons,
        train_size=train_size,
        exog_rows=exog_rows,
        timestamps=timestamps,
        refit_each_origin=refit_each_origin,
    )
    return {"ok": True, "preds": preds, "site_id": site_id, "model_label": model_label}


def _model_category(model_name: str) -> str:
    name = model_name.lower()
    if name in ("lightgbm", "xgboost"):
        return "boost"
    if name in ("random_forest",):
        return "forest"
    if name in ("mlp",):
        return "nn"
    if name in ("linear_ar", "linear_exog"):
        return "linear"
    return "baseline"


def run_experiment(
    config: dict,
    dataset: dict,
    dataset_stats: dict | None = None,
) -> dict:
    logger = get_logger("wpf.orchestrator")

    exp_cfg = config.get("experiment", {})
    models_cfg = config.get("models", [])

    exp_name = exp_cfg.get("name", "demo_experiment")
    dataset_version = exp_cfg.get("dataset_version", "demo_dataset_v1")
    train_size = int(exp_cfg.get("train_size", 120))
    refit_each_origin = bool(exp_cfg.get("refit_each_origin", True))
    skip_failed_models = bool(exp_cfg.get("skip_failed_models", True))
    max_workers = int(exp_cfg.get("max_workers", 1))
    model_type_limits = exp_cfg.get("model_type_limits", {}) or {}
    search_seed = int(exp_cfg.get("search_seed", 42))
    horizons = list(exp_cfg.get("horizons", [1, 2, 4]))
    sites = list(exp_cfg.get("sites", list(dataset.keys())))
    model_specs = _expand_model_specs_with_seed(models_cfg=models_cfg, seed=search_seed)

    run_tag = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = f"outputs/runs/{exp_name}_{run_tag}"

    logger.info(
        "Experiment=%s, sites=%s, model_variants=%s",
        exp_name,
        sites,
        len(model_specs),
    )

    tasks: list[dict] = []
    for model_cfg in model_specs:
        model_name = model_cfg["name"]
        params = model_cfg["params"]
        model_label = model_cfg["label"]
        for site_id in sites:
            raw_payload = dataset[site_id]
            if isinstance(raw_payload, dict) and "series" in raw_payload:
                series = list(raw_payload["series"])
                exog_rows = raw_payload.get("exog")
                timestamps = raw_payload.get("timestamps")
            else:
                series = list(raw_payload)
                exog_rows = None
                timestamps = None
            tasks.append(
                {
                    "model_name": model_name,
                    "params": params,
                    "model_label": model_label,
                    "site_id": site_id,
                    "series": series,
                    "exog_rows": exog_rows,
                    "timestamps": timestamps,
                    "horizons": horizons,
                    "train_size": train_size,
                    "refit_each_origin": refit_each_origin,
                }
            )

    all_preds: list[dict] = []
    failed_models: list[dict] = []
    if max_workers <= 1:
        for task in tasks:
            try:
                res = _run_single_task(task)
                all_preds.extend(res["preds"])
            except Exception as exc:
                if not skip_failed_models:
                    raise
                failed_models.append(
                    {
                        "model_name": task["model_name"],
                        "model_label": task["model_label"],
                        "site_id": task["site_id"],
                        "error": str(exc),
                    }
                )
                logger.warning(
                    "Skip model %s on site %s: %s",
                    task["model_label"],
                    task["site_id"],
                    exc,
                )
    else:
        semaphores: dict[str, threading.Semaphore] = {}
        for cat in ("boost", "forest", "nn", "linear", "baseline"):
            limit = int(model_type_limits.get(cat, max_workers))
            semaphores[cat] = threading.Semaphore(max(1, limit))

        def submit_with_limit(task: dict) -> dict:
            cat = _model_category(task["model_name"])
            sem = semaphores.get(cat)
            if sem is None:
                return _run_single_task(task)
            with sem:
                return _run_single_task(task)

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            future_map = {ex.submit(submit_with_limit, task): task for task in tasks}
            for fut in as_completed(future_map):
                try:
                    res = fut.result()
                    all_preds.extend(res["preds"])
                except Exception as exc:
                    if not skip_failed_models:
                        raise
                    msg = str(exc)
                    task = future_map[fut]
                    failed_models.append(
                        {
                            "model_name": task["model_name"],
                            "model_label": task["model_label"],
                            "site_id": task["site_id"],
                            "error": msg,
                        }
                    )
                    logger.warning(
                        "Skip model %s on site %s: %s",
                        task["model_label"],
                        task["site_id"],
                        msg,
                    )

    if not all_preds:
        raise RuntimeError("No successful model predictions generated. Check dependencies and configs.")

    metric_rows = evaluate(all_preds)
    leaderboard = build_leaderboard(metric_rows)
    stability_rows = build_stability_leaderboard(metric_rows)

    write_csv(f"{out_dir}/predictions.csv", all_preds)
    write_csv(f"{out_dir}/metrics.csv", metric_rows)
    write_csv(f"{out_dir}/leaderboard.csv", leaderboard)
    write_csv(f"{out_dir}/stability_leaderboard.csv", stability_rows)
    if failed_models:
        write_json(f"{out_dir}/failed_models.json", {"failed_models": failed_models})
    if dataset_stats:
        write_json(f"{out_dir}/dataset_profile.json", dataset_stats)
    write_json(
        f"{out_dir}/run_summary.json",
        {
            "experiment": exp_name,
            "dataset_version": dataset_version,
            "horizons": horizons,
            "sites": sites,
            "models": model_specs,
            "output_dir": out_dir,
            "refit_each_origin": refit_each_origin,
            "max_workers": max_workers,
            "model_type_limits": model_type_limits,
            "skip_failed_models": skip_failed_models,
            "failed_models": failed_models,
            "dataset_stats": dataset_stats or {},
        },
    )
    report_md = build_markdown_report(
        experiment=exp_name,
        dataset_version=dataset_version,
        leaderboard_rows=leaderboard,
        metric_rows=metric_rows,
        stability_rows=stability_rows,
        failed_models=failed_models,
    )
    from pathlib import Path

    report_path = Path(out_dir) / "report.md"
    report_path.write_text(report_md, encoding="utf-8")

    if dataset:
        first_site = sites[0]
        first_payload = dataset[first_site]
        first_series = first_payload["series"] if isinstance(first_payload, dict) else first_payload
        registry = DatasetRegistry()
        registry.register(
            dataset_version_id=dataset_version,
            site_ids=sites,
            time_start="t0",
            time_end=f"t{len(first_series) - 1}",
            notes="demo synthetic data",
        )

    logger.info("Run completed. Output=%s", out_dir)
    return {
        "output_dir": out_dir,
        "leaderboard": leaderboard,
        "metrics": metric_rows,
        "stability": stability_rows,
    }
