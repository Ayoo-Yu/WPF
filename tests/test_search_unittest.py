from __future__ import annotations

import unittest

from src.core.orchestrator import _expand_model_specs_with_seed


class SearchExpansionTest(unittest.TestCase):
    def test_random_search_respects_max_trials(self) -> None:
        models_cfg = [
            {
                "name": "lightgbm",
                "search": {"method": "random", "max_trials": 3},
                "params_grid": {
                    "lags": [8, 12, 16],
                    "learning_rate": [0.03, 0.05],
                },
            }
        ]

        specs = _expand_model_specs_with_seed(models_cfg=models_cfg, seed=42)
        self.assertEqual(len(specs), 3)
        self.assertTrue(all(s["name"] == "lightgbm" for s in specs))

    def test_grid_search_can_be_truncated(self) -> None:
        models_cfg = [
            {
                "name": "random_forest",
                "search": {"method": "grid", "max_trials": 2},
                "params_grid": {"lags": [4, 8], "max_depth": [6, 10]},
            }
        ]
        specs = _expand_model_specs_with_seed(models_cfg=models_cfg, seed=7)
        self.assertEqual(len(specs), 2)


if __name__ == "__main__":
    unittest.main()
