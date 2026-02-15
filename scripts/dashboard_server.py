from __future__ import annotations

import json
import os
import subprocess
import shutil
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import csv
from datetime import datetime, UTC
import threading
import uuid

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
OUTPUTS_DIR = ROOT / "outputs" / "runs"
CONFIGS_DIR = ROOT / "configs" / "experiments"


@dataclass
class ApiResponse:
    status: int
    payload: dict


class RunTaskStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, dict] = {}

    def create(self, config_path: str) -> dict:
        task_id = uuid.uuid4().hex
        task = {
            "task_id": task_id,
            "status": "queued",
            "config_path": config_path,
            "created_at": datetime.now(UTC).isoformat(),
            "started_at": "",
            "finished_at": "",
            "output_dir": "",
            "error": "",
            "stdout": "",
            "stderr": "",
        }
        with self._lock:
            self._tasks[task_id] = task
        return dict(task)

    def get(self, task_id: str) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            return dict(task) if task else None

    def update(self, task_id: str, **fields) -> dict | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.update(fields)
            return dict(task)


RUN_TASKS = RunTaskStore()


def _extract_output_dir(stdout: str) -> str:
    for line in stdout.splitlines():
        if line.startswith("Output dir:"):
            return line.split("Output dir:", 1)[1].strip()
    return ""


def _run_demo_task(task_id: str, config_rel: str) -> None:
    RUN_TASKS.update(task_id, status="running", started_at=datetime.now(UTC).isoformat())
    cmd = ["python3", "scripts/run_demo.py", "--config", config_rel]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        output_dir = _extract_output_dir(proc.stdout)
        status = "succeeded" if proc.returncode == 0 else "failed"
        error = "" if proc.returncode == 0 else "Demo run failed"
        RUN_TASKS.update(
            task_id,
            status=status,
            finished_at=datetime.now(UTC).isoformat(),
            output_dir=output_dir,
            error=error,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except Exception as exc:
        RUN_TASKS.update(
            task_id,
            status="failed",
            finished_at=datetime.now(UTC).isoformat(),
            error=str(exc),
            stderr=str(exc),
        )


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            response = self.handle_api_get(parsed)
            self.respond_json(response)
            return

        if parsed.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/run", "/api/cleanup"):
            self.respond_json(ApiResponse(HTTPStatus.NOT_FOUND, {"error": "Not found"}))
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.respond_json(ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"}))
            return

        if parsed.path == "/api/cleanup":
            response = self.handle_cleanup(body)
            self.respond_json(response)
            return

        config_path = str(body.get("config_path", "configs/experiments/real_data_demo.yaml")).strip()
        cfg_abs = (ROOT / config_path).resolve()
        if not cfg_abs.exists() or not cfg_abs.is_file() or ROOT not in cfg_abs.parents:
            self.respond_json(
                ApiResponse(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Invalid config_path: must be a file under project root"},
                )
            )
            return

        config_rel = str(cfg_abs.relative_to(ROOT))
        task = RUN_TASKS.create(config_rel)
        t = threading.Thread(target=_run_demo_task, args=(task["task_id"], config_rel), daemon=True)
        t.start()

        self.respond_json(
            ApiResponse(
                HTTPStatus.OK,
                {
                    "message": "Run accepted",
                    "task_id": task["task_id"],
                    "status": task["status"],
                },
            )
        )

    def handle_cleanup(self, body: dict) -> ApiResponse:
        keep_latest = int(body.get("keep_latest", 20))
        dry_run = bool(body.get("dry_run", True))
        prefix = str(body.get("prefix", "")).strip()
        if keep_latest < 0:
            return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "keep_latest must be >= 0"})

        runs = self.list_runs()
        if prefix:
            runs = [r for r in runs if str(r.get("run_id", "")).startswith(prefix)]

        to_delete = runs[keep_latest:]
        deleted: list[str] = []
        failed: list[dict] = []

        if not dry_run:
            for row in to_delete:
                run_id = str(row["run_id"])
                target = OUTPUTS_DIR / run_id
                try:
                    if target.exists() and target.is_dir():
                        shutil.rmtree(target)
                        deleted.append(run_id)
                except OSError as exc:
                    failed.append({"run_id": run_id, "error": str(exc)})

        return ApiResponse(
            HTTPStatus.OK,
            {
                "dry_run": dry_run,
                "prefix": prefix,
                "keep_latest": keep_latest,
                "candidate_count": len(to_delete),
                "candidates": [r["run_id"] for r in to_delete],
                "deleted_count": len(deleted),
                "deleted": deleted,
                "failed": failed,
            },
        )

    def handle_api_get(self, parsed) -> ApiResponse:
        if parsed.path == "/api/configs":
            configs = self.list_configs()
            return ApiResponse(HTTPStatus.OK, {"configs": configs})

        if parsed.path == "/api/storage_summary":
            return ApiResponse(HTTPStatus.OK, self.storage_summary())

        if parsed.path == "/api/config_text":
            params = parse_qs(parsed.query)
            path_rel = params.get("path", [""])[0]
            if not path_rel:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "path is required"})
            cfg = (ROOT / path_rel).resolve()
            if not cfg.exists() or not cfg.is_file() or ROOT not in cfg.parents:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "Invalid path"})
            try:
                text = cfg.read_text(encoding="utf-8")
            except OSError:
                text = ""
            return ApiResponse(HTTPStatus.OK, {"text": text})

        if parsed.path == "/api/runs":
            runs = self.list_runs()
            return ApiResponse(HTTPStatus.OK, {"runs": runs})

        if parsed.path == "/api/run_task":
            params = parse_qs(parsed.query)
            task_id = params.get("task_id", [""])[0]
            if not task_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "task_id is required"})
            task = RUN_TASKS.get(task_id)
            if task is None:
                return ApiResponse(HTTPStatus.NOT_FOUND, {"error": "task not found"})
            return ApiResponse(HTTPStatus.OK, task)

        if parsed.path == "/api/run_summary":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            summary_fp = OUTPUTS_DIR / run_id / "run_summary.json"
            summary = self.read_json_safe(summary_fp, default={})
            return ApiResponse(HTTPStatus.OK, {"summary": summary})

        if parsed.path == "/api/report":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            report_fp = OUTPUTS_DIR / run_id / "report.md"
            if not report_fp.exists():
                return ApiResponse(HTTPStatus.OK, {"report": ""})
            try:
                text = report_fp.read_text(encoding="utf-8")
            except OSError:
                text = ""
            return ApiResponse(HTTPStatus.OK, {"report": text})

        if parsed.path == "/api/artifacts":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            run_dir = OUTPUTS_DIR / run_id
            if not run_dir.exists() or not run_dir.is_dir():
                return ApiResponse(HTTPStatus.OK, {"artifacts": []})
            rows = []
            for p in sorted(run_dir.iterdir()):
                if not p.is_file():
                    continue
                rows.append({"name": p.name, "size": p.stat().st_size})
            return ApiResponse(HTTPStatus.OK, {"artifacts": rows})

        if parsed.path == "/api/best_model_trend":
            params = parse_qs(parsed.query)
            limit = int(params.get("limit", ["12"])[0] or "12")
            trend = self.best_model_trend(limit=max(1, min(limit, 200)))
            return ApiResponse(HTTPStatus.OK, {"rows": trend})

        if parsed.path in ("/api/leaderboard", "/api/metrics", "/api/stability"):
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})

            if parsed.path.endswith("leaderboard"):
                filename = "leaderboard.csv"
            elif parsed.path.endswith("stability"):
                filename = "stability_leaderboard.csv"
            else:
                filename = "metrics.csv"
            csv_path = OUTPUTS_DIR / run_id / filename
            if not csv_path.exists():
                if parsed.path.endswith("stability"):
                    # Old runs may not have stability_leaderboard.csv.
                    return ApiResponse(HTTPStatus.OK, {"rows": []})
                return ApiResponse(HTTPStatus.NOT_FOUND, {"error": f"File not found: {csv_path}"})

            rows = self.read_csv(csv_path)
            return ApiResponse(HTTPStatus.OK, {"rows": rows})

        if parsed.path == "/api/failed_models":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            fp = OUTPUTS_DIR / run_id / "failed_models.json"
            payload = {"failed_models": []}
            if fp.exists():
                try:
                    payload = json.loads(fp.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {"failed_models": []}
            else:
                summary_fp = OUTPUTS_DIR / run_id / "run_summary.json"
                if summary_fp.exists():
                    try:
                        summary = json.loads(summary_fp.read_text(encoding="utf-8"))
                        payload = {"failed_models": summary.get("failed_models", [])}
                    except json.JSONDecodeError:
                        payload = {"failed_models": []}
            return ApiResponse(HTTPStatus.OK, payload)

        if parsed.path == "/api/dataset_profile":
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})
            profile_path = OUTPUTS_DIR / run_id / "dataset_profile.json"
            if not profile_path.exists():
                return ApiResponse(HTTPStatus.OK, {"profile": {}})
            try:
                profile = json.loads(profile_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return ApiResponse(HTTPStatus.OK, {"profile": {}})
            return ApiResponse(HTTPStatus.OK, {"profile": profile})

        return ApiResponse(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def list_runs(self) -> list[dict]:
        if not OUTPUTS_DIR.exists():
            return []

        rows: list[dict] = []
        for d in OUTPUTS_DIR.iterdir():
            if not d.is_dir():
                continue
            summary = d / "run_summary.json"
            row = {"run_id": d.name, "has_summary": summary.exists()}
            if summary.exists():
                try:
                    data = json.loads(summary.read_text(encoding="utf-8"))
                    row["experiment"] = data.get("experiment", "")
                    row["dataset_version"] = data.get("dataset_version", "")
                    row["failed_count"] = len(data.get("failed_models", []))
                except json.JSONDecodeError:
                    row["experiment"] = ""
                    row["dataset_version"] = ""
                    row["failed_count"] = 0
            else:
                row["failed_count"] = 0
            rows.append(row)

        rows.sort(key=lambda x: x["run_id"], reverse=True)
        return rows

    def list_configs(self) -> list[str]:
        if not CONFIGS_DIR.exists():
            return []
        rows = []
        for p in CONFIGS_DIR.glob("*.yaml"):
            rows.append(str(p.relative_to(ROOT)))
        rows.sort()
        return rows

    def best_model_trend(self, limit: int = 12) -> list[dict]:
        runs = self.list_runs()[:limit]
        rows: list[dict] = []
        for r in runs:
            run_id = r["run_id"]
            lb_fp = OUTPUTS_DIR / run_id / "leaderboard.csv"
            best_model = ""
            best_mae = ""
            if lb_fp.exists():
                try:
                    lb_rows = self.read_csv(lb_fp)
                    if lb_rows:
                        sorted_rows = sorted(lb_rows, key=lambda x: float(x.get("avg_MAE", "1e18")))
                        top = sorted_rows[0]
                        best_model = str(top.get("model_name", ""))
                        best_mae = str(top.get("avg_MAE", ""))
                except Exception:
                    best_model = ""
                    best_mae = ""
            rows.append(
                {
                    "run_id": run_id,
                    "experiment": r.get("experiment", ""),
                    "best_model": best_model,
                    "best_avg_MAE": best_mae,
                    "failed_count": r.get("failed_count", 0),
                }
            )
        return rows

    def storage_summary(self) -> dict:
        if not OUTPUTS_DIR.exists():
            return {"run_count": 0, "total_bytes": 0, "newest_run": "", "oldest_run": ""}
        dirs = [p for p in OUTPUTS_DIR.iterdir() if p.is_dir()]
        run_ids = sorted([d.name for d in dirs])
        total_bytes = 0
        for d in dirs:
            for f in d.rglob("*"):
                if f.is_file():
                    total_bytes += f.stat().st_size
        return {
            "run_count": len(dirs),
            "total_bytes": total_bytes,
            "newest_run": run_ids[-1] if run_ids else "",
            "oldest_run": run_ids[0] if run_ids else "",
        }

    @staticmethod
    def read_json_safe(path: Path, default: dict | list) -> dict | list:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default

    @staticmethod
    def read_csv(path: Path) -> list[dict]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(r) for r in reader]

    def respond_json(self, response: ApiResponse) -> None:
        payload = json.dumps(response.payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(response.status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    host = os.environ.get("WPF_HOST", "127.0.0.1")
    port = int(os.environ.get("WPF_PORT", "8000"))
    server = ThreadingHTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
