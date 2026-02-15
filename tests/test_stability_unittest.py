from __future__ import annotations

import unittest

from src.core.stability import build_stability_leaderboard


class StabilityLeaderboardTest(unittest.TestCase):
    def test_build_stability_leaderboard_overall_only(self) -> None:
        metric_rows = [
            {
                "site_id": "s1",
                "model_name": "m1",
                "segment_key": "overall",
                "segment_value": "all",
                "MAE": 1.0,
                "RMSE": 2.0,
                "nMAE": 0.1,
            },
            {
                "site_id": "s1",
                "model_name": "m1",
                "segment_key": "overall",
                "segment_value": "all",
                "MAE": 2.0,
                "RMSE": 3.0,
                "nMAE": 0.2,
            },
            {
                "site_id": "s1",
                "model_name": "m1",
                "segment_key": "season",
                "segment_value": "summer",
                "MAE": 9.9,
                "RMSE": 9.9,
                "nMAE": 0.9,
            },
        ]

        rows = build_stability_leaderboard(metric_rows)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["site_id"], "s1")
        self.assertEqual(row["model_name"], "m1")
        self.assertAlmostEqual(float(row["mean_MAE"]), 1.5, places=6)
        self.assertEqual(int(row["horizon_count"]), 2)


if __name__ == "__main__":
    unittest.main()
