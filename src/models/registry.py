from __future__ import annotations

from src.models.base import ForecastModel
from src.models.moving_average import MovingAverageModel
from src.models.persistence import PersistenceModel


MODEL_REGISTRY: dict[str, type[ForecastModel]] = {
    "persistence": PersistenceModel,
    "moving_average": MovingAverageModel,
}


def create_model(name: str, params: dict | None = None) -> ForecastModel:
    if name not in MODEL_REGISTRY:
        supported = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(f"Unknown model '{name}'. Supported: {supported}")
    return MODEL_REGISTRY[name](params=params)
