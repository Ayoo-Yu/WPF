from __future__ import annotations

import unittest

from src.data.csv_loader import load_scada_nwp_series


class CsvLoaderTest(unittest.TestCase):
    def test_csv_loader_aligns_scada_and_nwp(self) -> None:
        result = load_scada_nwp_series(
            scada_csv="test_scada.csv",
            nwp_csv="test_nwp.csv",
            site_id="site_test_01",
            target_col="Total_Power",
            timestamp_col="Timestamp",
            max_rows=1000,
        )

        self.assertEqual(len(result.series), 1000)
        self.assertEqual(len(result.timestamps), 1000)
        self.assertEqual(len(result.exog_rows), 1000)
        self.assertEqual(result.stats["rows_aligned"], 1000)
        self.assertGreater(int(result.stats["n_exog_features"]), 0)
        self.assertGreaterEqual(float(result.stats["target_max"]), float(result.stats["target_min"]))


if __name__ == "__main__":
    unittest.main()
