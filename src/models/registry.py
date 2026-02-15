from __future__ import annotations

from src.models.base import ForecastModel
from src.models.lightgbm_model import LightGBMModel
from src.models.linear_ar import LinearARModel
from src.models.linear_exog import LinearExogModel
from src.models.mlp import MLPModel
from src.models.moving_average import MovingAverageModel
from src.models.persistence import PersistenceModel
from src.models.random_forest import RandomForestModel
from src.models.xgboost_model import XGBoostModel


MODEL_REGISTRY: dict[str, type[ForecastModel]] = {
    "lightgbm": LightGBMModel,
    "linear_ar": LinearARModel,
    "linear_exog": LinearExogModel,
    "mlp": MLPModel,
    "persistence": PersistenceModel,
    "moving_average": MovingAverageModel,
    "random_forest": RandomForestModel,
    "xgboost": XGBoostModel,
}


def create_model(name: str, params: dict | None = None) -> ForecastModel:
    if name not in MODEL_REGISTRY:
        supported = ", ".join(sorted(MODEL_REGISTRY.keys()))
        raise ValueError(f"Unknown model '{name}'. Supported: {supported}")
    return MODEL_REGISTRY[name](params=params)
