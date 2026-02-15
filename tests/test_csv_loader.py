from __future__ import annotations

from src.data.csv_loader import load_scada_nwp_series


def test_csv_loader_aligns_scada_and_nwp() -> None:
    result = load_scada_nwp_series(
        scada_csv="test_scada.csv",
        nwp_csv="test_nwp.csv",
        site_id="site_test_01",
        target_col="Total_Power",
        timestamp_col="Timestamp",
        max_rows=1000,
    )

    assert len(result.series) == 1000
    assert len(result.timestamps) == 1000
    assert len(result.exog_rows) == 1000
    assert result.stats["rows_aligned"] == 1000
    assert int(result.stats["n_exog_features"]) > 0
    assert float(result.stats["target_max"]) >= float(result.stats["target_min"])
