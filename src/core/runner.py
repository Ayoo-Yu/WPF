from __future__ import annotations

from src.models.base import ForecastModel


def run_backtest(
    series: list[float],
    site_id: str,
    model: ForecastModel,
    model_label: str,
    horizons: list[int],
    train_size: int,
    exog_rows: list[dict[str, float]] | None = None,
    timestamps: list[str] | None = None,
    refit_each_origin: bool = True,
) -> list[dict]:
    if not horizons:
        raise ValueError("horizons must not be empty")

    max_h = max(horizons)
    rows: list[dict] = []
    if not refit_each_origin:
        exog_history = exog_rows[:train_size] if exog_rows else None
        model.fit(series[:train_size], exog_history=exog_history)

    for origin in range(train_size, len(series) - max_h + 1):
        history = series[:origin]
        if refit_each_origin:
            exog_history = exog_rows[:origin] if exog_rows else None
            model.fit(history, exog_history=exog_history)
        for h in horizons:
            y_true = series[origin + h - 1]
            idx = origin + h - 1
            exog_future = exog_rows[idx] if exog_rows and idx < len(exog_rows) else None
            exog_future_seq = (
                [exog_rows[origin + step] if origin + step < len(exog_rows) else None for step in range(h)]
                if exog_rows
                else None
            )
            y_pred = model.predict(
                history,
                h,
                exog_future=exog_future,
                exog_future_seq=exog_future_seq,
            )
            wind_speed = None
            if exog_future:
                if "wind_speed100_10" in exog_future:
                    wind_speed = exog_future["wind_speed100_10"]
                elif "wind_speed10_10" in exog_future:
                    wind_speed = exog_future["wind_speed10_10"]

            rows.append(
                {
                    "site_id": site_id,
                    "model_name": model_label,
                    "origin_index": origin,
                    "horizon": h,
                    "timestamp": timestamps[idx] if timestamps and idx < len(timestamps) else "",
                    "wind_speed": float(wind_speed) if wind_speed is not None else "",
                    "y_true": float(y_true),
                    "y_pred": float(y_pred),
                }
            )
    return rows
