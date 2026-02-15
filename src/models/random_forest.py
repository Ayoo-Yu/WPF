from __future__ import annotations

from src.models.tabular_forecast import TabularAutoregModel


class RandomForestModel(TabularAutoregModel):
    @property
    def name(self) -> str:
        return "random_forest"

    def _make_estimator(self):
        try:
            from sklearn.ensemble import RandomForestRegressor
        except ImportError as exc:
            raise RuntimeError("random_forest requires scikit-learn") from exc

        n_estimators = int(self.params.get("n_estimators", 300))
        max_depth = self.params.get("max_depth")
        max_features = self.params.get("max_features", "sqrt")
        random_state = int(self.params.get("random_state", 42))
        n_jobs = int(self.params.get("n_jobs", -1))

        return RandomForestRegressor(
            n_estimators=n_estimators,
            max_depth=None if max_depth in (None, "None") else int(max_depth),
            max_features=max_features,
            random_state=random_state,
            n_jobs=n_jobs,
        )
