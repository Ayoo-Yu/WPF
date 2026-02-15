from __future__ import annotations

from src.models.tabular_forecast import TabularAutoregModel


def _parse_hidden_layers(value: object) -> tuple[int, ...]:
    if isinstance(value, (list, tuple)) and value:
        return tuple(int(v) for v in value)
    if isinstance(value, int):
        return (value,)
    return (64, 32)


class MLPModel(TabularAutoregModel):
    @property
    def name(self) -> str:
        return "mlp"

    def _make_estimator(self):
        try:
            from sklearn.neural_network import MLPRegressor
        except ImportError as exc:
            raise RuntimeError("mlp requires scikit-learn") from exc

        hidden_layer_sizes = _parse_hidden_layers(self.params.get("hidden_layer_sizes", [64, 32]))
        learning_rate_init = float(self.params.get("learning_rate_init", 0.001))
        max_iter = int(self.params.get("max_iter", 300))
        alpha = float(self.params.get("alpha", 0.0001))
        random_state = int(self.params.get("random_state", 42))

        return MLPRegressor(
            hidden_layer_sizes=hidden_layer_sizes,
            learning_rate_init=learning_rate_init,
            max_iter=max_iter,
            alpha=alpha,
            random_state=random_state,
        )
