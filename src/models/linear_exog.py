from __future__ import annotations

from src.models.base import ForecastModel


class LinearExogModel(ForecastModel):
    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params=params)
        self.coef: list[float] | None = None
        self.feature_cols: list[str] = []

    @property
    def name(self) -> str:
        return "linear_exog"

    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        lags = int(self.params.get("lags", 12))
        if lags < 1 or len(train_series) <= lags:
            self.coef = None
            return
        if not exog_history or len(exog_history) < len(train_series):
            self.coef = None
            return

        feature_cols = self.params.get("feature_cols", [])
        if not feature_cols:
            # Use all columns from first row if caller didn't specify.
            feature_cols = sorted(exog_history[0].keys())
        self.feature_cols = [str(c) for c in feature_cols]

        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError("linear_exog model requires numpy") from exc

        x_rows: list[list[float]] = []
        y_vals: list[float] = []
        for t in range(lags, len(train_series)):
            feat = [1.0]
            feat.extend(train_series[t - i] for i in range(1, lags + 1))
            ex = exog_history[t]
            feat.extend(float(ex.get(col, 0.0)) for col in self.feature_cols)
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
        if len(history) < lags:
            return history[-1]

        sim = list(history)
        offset = 1 + lags
        for step in range(horizon):
            if len(sim) < lags:
                sim.append(sim[-1])
                continue

            ex = exog_future or {}
            if exog_future_seq and step < len(exog_future_seq):
                ex = exog_future_seq[step] or {}

            val = self.coef[0]
            for i in range(lags):
                val += self.coef[i + 1] * sim[-1 - i]
            for j, col in enumerate(self.feature_cols):
                val += self.coef[offset + j] * float(ex.get(col, 0.0))
            sim.append(float(val))

        return float(sim[-1])
