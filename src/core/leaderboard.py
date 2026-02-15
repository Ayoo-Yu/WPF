from __future__ import annotations


def build_leaderboard(metric_rows: list[dict]) -> list[dict]:
    agg: dict[tuple[str, str], dict[str, float]] = {}

    for row in metric_rows:
        key = (row["site_id"], row["model_name"])
        if key not in agg:
            agg[key] = {"mae_sum": 0.0, "rmse_sum": 0.0, "count": 0.0}
        agg[key]["mae_sum"] += float(row["MAE"])
        agg[key]["rmse_sum"] += float(row["RMSE"])
        agg[key]["count"] += 1.0

    board: list[dict] = []
    for (site_id, model_name), v in agg.items():
        c = max(v["count"], 1.0)
        board.append(
            {
                "site_id": site_id,
                "model_name": model_name,
                "avg_MAE": round(v["mae_sum"] / c, 6),
                "avg_RMSE": round(v["rmse_sum"] / c, 6),
            }
        )

    return sorted(board, key=lambda x: (x["site_id"], x["avg_MAE"]))
