from __future__ import annotations

import math


def _mean(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return sum(vals) / len(vals)


def _std(vals: list[float]) -> float:
    if len(vals) <= 1:
        return 0.0
    m = _mean(vals)
    var = sum((v - m) ** 2 for v in vals) / len(vals)
    return math.sqrt(var)


def build_stability_leaderboard(metric_rows: list[dict]) -> list[dict]:
    # Use overall rows only to avoid mixing segment semantics.
    filtered = [
        r
        for r in metric_rows
        if r.get("segment_key") == "overall" and r.get("segment_value") == "all"
    ]
    grouped: dict[tuple[str, str], dict[str, list[float]]] = {}
    for row in filtered:
        key = (str(row["site_id"]), str(row["model_name"]))
        if key not in grouped:
            grouped[key] = {"MAE": [], "RMSE": [], "nMAE": []}
        grouped[key]["MAE"].append(float(row["MAE"]))
        grouped[key]["RMSE"].append(float(row["RMSE"]))
        grouped[key]["nMAE"].append(float(row.get("nMAE", 0.0)))

    rows: list[dict] = []
    for (site_id, model_name), vals in grouped.items():
        mae_mean = _mean(vals["MAE"])
        mae_std = _std(vals["MAE"])
        rmse_mean = _mean(vals["RMSE"])
        nmae_mean = _mean(vals["nMAE"])
        cv = mae_std / mae_mean if mae_mean > 1e-12 else 0.0
        rows.append(
            {
                "site_id": site_id,
                "model_name": model_name,
                "mean_MAE": round(mae_mean, 6),
                "std_MAE": round(mae_std, 6),
                "cv_MAE": round(cv, 6),
                "mean_RMSE": round(rmse_mean, 6),
                "mean_nMAE": round(nmae_mean, 6),
                "horizon_count": len(vals["MAE"]),
            }
        )
    return sorted(rows, key=lambda x: (x["site_id"], x["cv_MAE"], x["mean_MAE"]))
