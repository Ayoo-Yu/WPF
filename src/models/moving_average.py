from __future__ import annotations

from src.models.base import ForecastModel


class MovingAverageModel(ForecastModel):
    @property
    def name(self) -> str:
        return "moving_average"

    def fit(self, train_series: list[float]) -> None:
        return

    def predict(self, history: list[float], horizon: int) -> float:
        window = int(self.params.get("window", 6))
        if not history:
            return 0.0
        segment = history[-window:] if len(history) > window else history
        return sum(segment) / len(segment)
