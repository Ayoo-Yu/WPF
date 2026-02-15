from __future__ import annotations

from collections import defaultdict


def _top_rows(rows: list[dict], n: int = 5) -> list[dict]:
    def key(row: dict) -> tuple:
        return (str(row.get("site_id", "")), float(row.get("avg_MAE", 1e18)))

    return sorted(rows, key=key)[:n]


def _metric_summary(metric_rows: list[dict], segment_key: str) -> list[dict]:
    filtered = [r for r in metric_rows if r.get("segment_key") == segment_key]
    if not filtered:
        return []
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in filtered:
        by_model[str(row["model_name"])].append(row)

    summary: list[dict] = []
    for model, rows in by_model.items():
        mae = sum(float(r["MAE"]) for r in rows) / len(rows)
        rmse = sum(float(r["RMSE"]) for r in rows) / len(rows)
        nmae = sum(float(r.get("nMAE", 0.0)) for r in rows) / len(rows)
        summary.append({"model_name": model, "MAE": mae, "RMSE": rmse, "nMAE": nmae})
    return sorted(summary, key=lambda x: x["MAE"])[:5]


def _render_table(rows: list[dict], cols: list[str]) -> str:
    if not rows:
        return "_无数据_"
    header = "| " + " | ".join(cols) + " |"
    split = "| " + " | ".join("---" for _ in cols) + " |"
    lines = [header, split]
    for row in rows:
        vals = []
        for c in cols:
            v = row.get(c, "")
            if isinstance(v, float):
                vals.append(f"{v:.6f}")
            else:
                vals.append(str(v))
        lines.append("| " + " | ".join(vals) + " |")
    return "\n".join(lines)


def build_markdown_report(
    experiment: str,
    dataset_version: str,
    leaderboard_rows: list[dict],
    metric_rows: list[dict],
    stability_rows: list[dict],
    failed_models: list[dict],
) -> str:
    lines: list[str] = []
    lines.append(f"# Run Report: {experiment}")
    lines.append("")
    lines.append(f"- dataset_version: `{dataset_version}`")
    lines.append(f"- leaderboard_rows: `{len(leaderboard_rows)}`")
    lines.append(f"- metric_rows: `{len(metric_rows)}`")
    lines.append(f"- failed_models: `{len(failed_models)}`")
    lines.append("")

    lines.append("## Top Leaderboard (overall)")
    lines.append("")
    lines.append(_render_table(_top_rows(leaderboard_rows, n=8), ["site_id", "model_name", "avg_MAE", "avg_RMSE", "avg_nMAE"]))
    lines.append("")

    lines.append("## Segment Summary: season")
    lines.append("")
    lines.append(_render_table(_metric_summary(metric_rows, "season"), ["model_name", "MAE", "RMSE", "nMAE"]))
    lines.append("")

    lines.append("## Segment Summary: wind_bin")
    lines.append("")
    lines.append(_render_table(_metric_summary(metric_rows, "wind_bin"), ["model_name", "MAE", "RMSE", "nMAE"]))
    lines.append("")

    lines.append("## Stability Leaderboard (overall across horizons)")
    lines.append("")
    lines.append(
        _render_table(
            stability_rows[:8],
            ["site_id", "model_name", "mean_MAE", "std_MAE", "cv_MAE", "mean_RMSE", "mean_nMAE"],
        )
    )
    lines.append("")

    lines.append("## Failed Models")
    lines.append("")
    if failed_models:
        lines.append(_render_table(failed_models, ["model_name", "model_label", "site_id", "error"]))
    else:
        lines.append("_None_")
    lines.append("")
    return "\n".join(lines)
