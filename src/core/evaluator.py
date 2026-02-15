from __future__ import annotations

import math
from datetime import datetime


def _mae(y_true: list[float], y_pred: list[float]) -> float:
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / len(y_true)


def _rmse(y_true: list[float], y_pred: list[float]) -> float:
    mse = sum((a - b) ** 2 for a, b in zip(y_true, y_pred)) / len(y_true)
    return math.sqrt(mse)


def _nmae(y_true: list[float], y_pred: list[float]) -> float:
    denom = max(sum(abs(v) for v in y_true), 1e-12)
    return sum(abs(a - b) for a, b in zip(y_true, y_pred)) / denom


def _season_from_ts(ts: str) -> str:
    if not ts:
        return "unknown"
    try:
        dt = datetime.strptime(ts.strip(), "%Y/%m/%d %H:%M")
    except ValueError:
        return "unknown"
    month = dt.month
    if month in (3, 4, 5):
        return "spring"
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "autumn"
    return "winter"


def _wind_bin(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 4.0:
        return "low"
    if value < 8.0:
        return "mid"
    return "high"


def evaluate(pred_rows: list[dict]) -> list[dict]:
    grouped: dict[tuple[str, str, int, str, str], dict[str, list[float]]] = {}

    for row in pred_rows:
        base = (row["site_id"], row["model_name"], row["horizon"])
        y_true = float(row["y_true"])
        y_pred = float(row["y_pred"])

        ts = str(row.get("timestamp", ""))
        season = _season_from_ts(ts)
        wind_raw = row.get("wind_speed")
        wind_val = None
        if wind_raw not in ("", None):
            try:
                wind_val = float(wind_raw)
            except (TypeError, ValueError):
                wind_val = None
        wind_bin = _wind_bin(wind_val)

        segments = [("overall", "all"), ("season", season), ("wind_bin", wind_bin)]
        for seg_key, seg_value in segments:
            key = (*base, seg_key, seg_value)
            grouped.setdefault(key, {"y_true": [], "y_pred": []})
            grouped[key]["y_true"].append(y_true)
            grouped[key]["y_pred"].append(y_pred)

    metrics: list[dict] = []
    for (site_id, model_name, horizon, seg_key, seg_value), values in grouped.items():
        y_true = values["y_true"]
        y_pred = values["y_pred"]
        if not y_true:
            continue
        metrics.append(
            {
                "site_id": site_id,
                "model_name": model_name,
                "horizon": horizon,
                "segment_key": seg_key,
                "segment_value": seg_value,
                "MAE": round(_mae(y_true, y_pred), 6),
                "RMSE": round(_rmse(y_true, y_pred), 6),
                "nMAE": round(_nmae(y_true, y_pred), 6),
                "samples": len(y_true),
            }
        )

    seg_order = {"overall": 0, "season": 1, "wind_bin": 2}
    return sorted(
        metrics,
        key=lambda x: (
            x["site_id"],
            seg_order.get(str(x["segment_key"]), 99),
            str(x["segment_value"]),
            int(x["horizon"]),
            float(x["MAE"]),
        ),
    )
