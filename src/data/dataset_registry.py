from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from src.utils.io import write_json


@dataclass
class DatasetVersion:
    dataset_version_id: str
    site_ids: list[str]
    time_start: str
    time_end: str
    created_at: str
    notes: str = ""


class DatasetRegistry:
    def __init__(self, path: str | Path = "outputs/runs/dataset_registry.json") -> None:
        self.path = Path(path)

    def register(
        self,
        dataset_version_id: str,
        site_ids: list[str],
        time_start: str,
        time_end: str,
        notes: str = "",
    ) -> dict[str, Any]:
        version = DatasetVersion(
            dataset_version_id=dataset_version_id,
            site_ids=site_ids,
            time_start=time_start,
            time_end=time_end,
            created_at=datetime.now(UTC).isoformat(),
            notes=notes,
        )
        payload = {"dataset_versions": [asdict(version)]}
        write_json(self.path, payload)
        return payload
