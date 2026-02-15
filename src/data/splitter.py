from __future__ import annotations


def generate_origins(total_length: int, train_size: int, max_horizon: int) -> list[int]:
    if train_size >= total_length:
        return []
    end = total_length - max_horizon + 1
    if end <= train_size:
        return []
    return list(range(train_size, end))
