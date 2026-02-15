from __future__ import annotations

from src.models.base import ForecastModel


class LinearARModel(ForecastModel):
    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params=params)
        self.coef: list[float] | None = None

    @property
    def name(self) -> str:
        return "linear_ar"

    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        lags = int(self.params.get("lags", 12))
        if lags < 1 or len(train_series) <= lags:
            self.coef = None
            return

        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("linear_ar model requires numpy") from exc

        x_rows: list[list[float]] = []
        y_vals: list[float] = []
        for t in range(lags, len(train_series)):
            feat = [1.0]
            feat.extend(train_series[t - i] for i in range(1, lags + 1))
            x_rows.append(feat)
            y_vals.append(train_series[t])

        x = np.asarray(x_rows, dtype=float)
        y = np.asarray(y_vals, dtype=float)
        if x.size == 0 or y.size == 0:
            self.coef = None
            return
        coef, *_ = np.linalg.lstsq(x, y, rcond=None)
        self.coef = [float(c) for c in coef]

    def predict(
        self,
        history: list[float],
        horizon: int,
        exog_future: dict[str, float] | None = None,
        exog_future_seq: list[dict[str, float] | None] | None = None,
    ) -> float:
        if not history:
            return 0.0
        if self.coef is None:
            return history[-1]

        lags = int(self.params.get("lags", 12))
        sim = list(history)
        for _ in range(horizon):
            if len(sim) < lags:
                sim.append(sim[-1])
                continue
            val = self.coef[0]
            for i in range(lags):
                val += self.coef[i + 1] * sim[-1 - i]
            sim.append(float(val))
        return float(sim[-1])
