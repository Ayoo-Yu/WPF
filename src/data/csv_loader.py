from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class CSVLoadResult:
    site_id: str
    series: list[float]
    timestamps: list[str]
    exog_rows: list[dict[str, float]]
    stats: dict[str, float | int | str]


def _parse_time(value: str) -> datetime:
    # Supports input like: 2023/1/1 0:15
    return datetime.strptime(value.strip(), "%Y/%m/%d %H:%M")


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [dict(r) for r in reader]


def _to_float(value: str) -> float | None:
    try:
        return float(value.strip())
    except (ValueError, AttributeError):
        return None


def load_scada_nwp_series(
    scada_csv: str | Path,
    nwp_csv: str | Path,
    site_id: str = "site_real_01",
    target_col: str = "Total_Power",
    timestamp_col: str = "Timestamp",
    max_rows: int | None = None,
) -> CSVLoadResult:
    scada_rows = _read_rows(scada_csv)
    nwp_rows = _read_rows(nwp_csv)
    if not scada_rows:
        raise ValueError(f"Empty scada csv: {scada_csv}")
    if not nwp_rows:
        raise ValueError(f"Empty nwp csv: {nwp_csv}")

    scada_by_ts: dict[str, dict[str, str]] = {}
    nwp_by_ts: dict[str, dict[str, str]] = {}
    for row in scada_rows:
        ts = row.get(timestamp_col, "").strip()
        if ts:
            scada_by_ts[ts] = row
    for row in nwp_rows:
        ts = row.get(timestamp_col, "").strip()
        if ts:
            nwp_by_ts[ts] = row

    common_ts = sorted(set(scada_by_ts.keys()) & set(nwp_by_ts.keys()), key=_parse_time)
    if max_rows is not None:
        common_ts = common_ts[: max(0, int(max_rows))]
    if not common_ts:
        raise ValueError("No aligned timestamps between scada and nwp csv")

    series: list[float] = []
    aligned_ts: list[str] = []
    exog_rows: list[dict[str, float]] = []
    dropped_target_nan = 0
    exog_feature_cols: list[str] = []
    for ts in common_ts:
        raw = scada_by_ts[ts].get(target_col, "").strip()
        try:
            y = float(raw)
        except ValueError:
            dropped_target_nan += 1
            continue

        nwp_row = nwp_by_ts[ts]
        exog: dict[str, float] = {}
        for k, v in nwp_row.items():
            if k == timestamp_col:
                continue
            fv = _to_float(v)
            if fv is None:
                continue
            exog[k] = fv
        if not exog_feature_cols and exog:
            exog_feature_cols = sorted(exog.keys())

        aligned_ts.append(ts)
        series.append(y)
        exog_rows.append(exog)

    if not series:
        raise ValueError(f"No valid target values in {target_col}")

    min_y = min(series)
    max_y = max(series)
    mean_y = sum(series) / len(series)

    stats: dict[str, float | int | str] = {
        "site_id": site_id,
        "target_col": target_col,
        "timestamp_col": timestamp_col,
        "rows_scada": len(scada_rows),
        "rows_nwp": len(nwp_rows),
        "rows_aligned": len(common_ts),
        "rows_final": len(series),
        "rows_dropped_target_parse": dropped_target_nan,
        "n_exog_features": len(exog_feature_cols),
        "target_min": round(min_y, 6),
        "target_max": round(max_y, 6),
        "target_mean": round(mean_y, 6),
        "time_start": aligned_ts[0],
        "time_end": aligned_ts[-1],
    }
    return CSVLoadResult(
        site_id=site_id,
        series=series,
        timestamps=aligned_ts,
        exog_rows=exog_rows,
        stats=stats,
    )
