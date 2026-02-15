from __future__ import annotations

from src.models.tabular_forecast import TabularAutoregModel


class XGBoostModel(TabularAutoregModel):
    @property
    def name(self) -> str:
        return "xgboost"

    def _make_estimator(self):
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise RuntimeError("xgboost model requires xgboost package") from exc

        return XGBRegressor(
            n_estimators=int(self.params.get("n_estimators", 500)),
            learning_rate=float(self.params.get("learning_rate", 0.05)),
            max_depth=int(self.params.get("max_depth", 6)),
            subsample=float(self.params.get("subsample", 0.9)),
            colsample_bytree=float(self.params.get("colsample_bytree", 0.9)),
            reg_lambda=float(self.params.get("reg_lambda", 1.0)),
            objective="reg:squarederror",
            random_state=int(self.params.get("random_state", 42)),
            n_jobs=int(self.params.get("n_jobs", -1)),
        )
