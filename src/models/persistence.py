from __future__ import annotations

from src.models.base import ForecastModel


class PersistenceModel(ForecastModel):
    @property
    def name(self) -> str:
        return "persistence"

    def fit(self, train_series: list[float]) -> None:
        return

    def predict(self, history: list[float], horizon: int) -> float:
        if not history:
            return 0.0
        if len(history) >= horizon:
            return history[-horizon]
        return history[-1]
