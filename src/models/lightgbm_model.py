from __future__ import annotations

from src.models.tabular_forecast import TabularAutoregModel


class LightGBMModel(TabularAutoregModel):
    @property
    def name(self) -> str:
        return "lightgbm"

    def _make_estimator(self):
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:
            raise RuntimeError("lightgbm model requires lightgbm package") from exc

        return LGBMRegressor(
            n_estimators=int(self.params.get("n_estimators", 500)),
            learning_rate=float(self.params.get("learning_rate", 0.05)),
            num_leaves=int(self.params.get("num_leaves", 31)),
            subsample=float(self.params.get("subsample", 0.9)),
            colsample_bytree=float(self.params.get("colsample_bytree", 0.9)),
            random_state=int(self.params.get("random_state", 42)),
        )
