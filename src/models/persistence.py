from __future__ import annotations

from src.models.base import ForecastModel


class PersistenceModel(ForecastModel):
    @property
    def name(self) -> str:
        return "persistence"

    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        return

    def predict(
        self,
        history: list[float],
        horizon: int,
        exog_future: dict[str, float] | None = None,
        exog_future_seq: list[dict[str, float] | None] | None = None,
    ) -> float:
        if not history:
            return 0.0
        if len(history) >= horizon:
            return history[-horizon]
        return history[-1]
