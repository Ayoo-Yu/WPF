from __future__ import annotations

from abc import ABC, abstractmethod


class ForecastModel(ABC):
    def __init__(self, params: dict | None = None) -> None:
        self.params = params or {}

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def fit(self, train_series: list[float], exog_history: list[dict[str, float]] | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        history: list[float],
        horizon: int,
        exog_future: dict[str, float] | None = None,
        exog_future_seq: list[dict[str, float] | None] | None = None,
    ) -> float:
        raise NotImplementedError
