from __future__ import annotations

from src.models.base import ForecastModel


def _to_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default


def _resolve_feature_cols(
    exog_history: list[dict[str, float]] | None,
    feature_cols_param: object,
) -> list[str]:
    if isinstance(feature_cols_param, list) and feature_cols_param:
        return [str(c) for c in feature_cols_param]
    if not exog_history:
        return []
    for row in exog_history:
        if row:
            return sorted(str(k) for k in row.keys())
    return []


class TabularAutoregModel(ForecastModel):
    estimator_name = "tabular_autoreg"

    def __init__(self, params: dict | None = None) -> None:
        super().__init__(params=params)
        self.estimator = None
        self.feature_cols: list[str] = []
        self.lags = int(self.params.get("lags", 12))

    def _make_estimator(self):
        raise NotImplementedError

    def _make_row(self, history: list[float], exog_row: dict[str, float] | None) -> list[float]:
        row = [history[-i] for i in range(1, self.lags + 1)]
        if self.feature_cols:
            ex = exog_row or {}
            row.extend(_to_float(ex.get(c, 0.0), 0.0) for c in self.feature_cols)
        return row

    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        if self.lags < 1 or len(train_series) <= self.lags:
            self.estimator = None
            return

        self.feature_cols = _resolve_feature_cols(exog_history, self.params.get("feature_cols"))
        x_rows: list[list[float]] = []
        y_vals: list[float] = []
        for t in range(self.lags, len(train_series)):
            ex_row = exog_history[t] if exog_history and t < len(exog_history) else None
            x_rows.append(self._make_row(train_series[:t], ex_row))
            y_vals.append(float(train_series[t]))

        if not x_rows:
            self.estimator = None
            return

        self.estimator = self._make_estimator()
        self.estimator.fit(x_rows, y_vals)

    def predict(
        self,
        history: list[float],
        horizon: int,
        exog_future: dict[str, float] | None = None,
        exog_future_seq: list[dict[str, float] | None] | None = None,
    ) -> float:
        if not history:
            return 0.0
        if self.estimator is None or len(history) < self.lags:
            return history[-1]

        sim = list(history)
        for step in range(horizon):
            ex_row = exog_future
            if exog_future_seq and step < len(exog_future_seq):
                ex_row = exog_future_seq[step]
            x = self._make_row(sim, ex_row)
            y_hat = float(self.estimator.predict([x])[0])
            sim.append(y_hat)
        return float(sim[-1])
