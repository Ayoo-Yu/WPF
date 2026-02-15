from __future__ import annotations

import math


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


def _rmse(y_true: list[float], y_pred: list[float]) -> float:
    mse = sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true)
    return math.sqrt(mse)


def evaluate(pred_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int], dict[str, list[float]]] = {}

    for row in pred_rows:
        key = (row["site_id"], row["model_name"], row["horizon"])
        grouped.setdefault(key, {"y_true": [], "y_pred": []})
        grouped[key]["y_true"].append(float(row["y_true"]))
        grouped[key]["y_pred"].append(float(row["y_pred"]))

    metrics: list[dict] = []
    for (site_id, model_name, horizon), values in grouped.items():
        y_true = values["y_true"]
        y_pred = values["y_pred"]
        if not y_true:
            continue
        metrics.append(
            {
                "site_id": site_id,
                "model_name": model_name,
                "horizon": horizon,
                "MAE": round(_mae(y_true, y_pred), 6),
                "RMSE": round(_rmse(y_true, y_pred), 6),
                "samples": len(y_true),
            }
        )

    return sorted(metrics, key=lambda x: (x["site_id"], x["horizon"], x["MAE"]))
