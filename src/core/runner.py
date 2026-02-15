from __future__ import annotations

from src.models.base import ForecastModel


def run_backtest(
    series: list[float],
    site_id: str,
    model: ForecastModel,
    horizons: list[int],
    train_size: int,
) -> list[dict]:
    if not horizons:
        raise ValueError("horizons must not be empty")

    max_h = max(horizons)
    rows: list[dict] = []

    for origin in range(train_size, len(series) - max_h + 1):
        history = series[:origin]
        model.fit(history)
        for h in horizons:
            y_true = series[origin + h - 1]
            y_pred = model.predict(history, h)
            rows.append(
                {
                    "site_id": site_id,
                    "model_name": model.name,
                    "origin_index": origin,
                    "horizon": h,
                    "y_true": float(y_true),
                    "y_pred": float(y_pred),
                }
            )
    return rows
