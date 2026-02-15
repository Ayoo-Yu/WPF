from __future__ import annotations

import unittest

from src.core.runner import run_backtest
from src.models.base import ForecastModel
from src.models.linear_exog import LinearExogModel


class _RecordingModel(ForecastModel):
    @property
    def name(self) -> str:
        return "recording"

    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        return

    def predict(
        self,
        history: list[float],
        horizon: int,
        exog_future: dict[str, float] | None = None,
        exog_future_seq: list[dict[str, float] | None] | None = None,
    ) -> float:
        if not hasattr(self, "calls"):
            self.calls = []
        self.calls.append(
            {
                "origin": len(history),
                "horizon": horizon,
                "exog_future": exog_future,
                "exog_future_seq": exog_future_seq,
            }
        )
        return float(history[-1]) if history else 0.0


class RunnerExogFutureSeqTest(unittest.TestCase):
    def test_run_backtest_passes_horizon_specific_exog_sequence(self) -> None:
        model = _RecordingModel()
        series = [1, 2, 3, 4, 5, 6]
        exog_rows = [{"f": float(i)} for i in range(len(series))]

        run_backtest(
            series=series,
            site_id="s1",
            model=model,
            model_label="recording",
            horizons=[1, 2],
            train_size=3,
            exog_rows=exog_rows,
            timestamps=None,
            refit_each_origin=True,
        )

        calls = getattr(model, "calls")
        first_h2 = next(c for c in calls if c["origin"] == 3 and c["horizon"] == 2)
        self.assertEqual(first_h2["exog_future"], {"f": 4.0})
        self.assertEqual(first_h2["exog_future_seq"], [{"f": 3.0}, {"f": 4.0}])

    def test_linear_exog_uses_exog_future_sequence_for_multistep(self) -> None:
        model = LinearExogModel(params={"lags": 1, "feature_cols": ["f"]})
        model.coef = [0.0, 0.0, 1.0]
        model.feature_cols = ["f"]

        y = model.predict(
            history=[10.0],
            horizon=2,
            exog_future={"f": 9.0},
            exog_future_seq=[{"f": 1.0}, {"f": 2.0}],
        )
        self.assertAlmostEqual(y, 2.0, places=6)


if __name__ == "__main__":
    unittest.main()
