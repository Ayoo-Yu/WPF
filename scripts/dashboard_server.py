from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import csv

ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = ROOT / "web"
OUTPUTS_DIR = ROOT / "outputs" / "runs"


@dataclass
class ApiResponse:
    status: int
    payload: dict


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
        if parsed.path != "/api/run":
            self.respond_json(ApiResponse(HTTPStatus.NOT_FOUND, {"error": "Not found"}))
            return

        content_len = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_len) if content_len > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.respond_json(ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON body"}))
            return

        config_path = body.get("config_path", "configs/experiments/demo.yaml")
        cfg_abs = (ROOT / config_path).resolve()
        if not cfg_abs.exists():
            self.respond_json(
                ApiResponse(
                    HTTPStatus.BAD_REQUEST,
                    {"error": f"Config not found: {config_path}"},
                )
            )
            return

        cmd = ["python3", "scripts/run_demo.py", "--config", config_path]
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )

        if proc.returncode != 0:
            self.respond_json(
                ApiResponse(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    {
                        "error": "Demo run failed",
                        "stdout": proc.stdout,
                        "stderr": proc.stderr,
                    },
                )
            )
            return

        output_dir = ""
        for line in proc.stdout.splitlines():
            if line.startswith("Output dir:"):
                output_dir = line.split("Output dir:", 1)[1].strip()
                break

        self.respond_json(
            ApiResponse(
                HTTPStatus.OK,
                {
                    "message": "Run completed",
                    "output_dir": output_dir,
                    "stdout": proc.stdout,
                },
            )
        )

    def handle_api_get(self, parsed) -> ApiResponse:
        if parsed.path == "/api/runs":
            runs = self.list_runs()
            return ApiResponse(HTTPStatus.OK, {"runs": runs})

        if parsed.path in ("/api/leaderboard", "/api/metrics"):
            params = parse_qs(parsed.query)
            run_id = params.get("run_id", [""])[0]
            if not run_id:
                return ApiResponse(HTTPStatus.BAD_REQUEST, {"error": "run_id is required"})

            filename = "leaderboard.csv" if parsed.path.endswith("leaderboard") else "metrics.csv"
            csv_path = OUTPUTS_DIR / run_id / filename
            if not csv_path.exists():
                return ApiResponse(HTTPStatus.NOT_FOUND, {"error": f"File not found: {csv_path}"})

            rows = self.read_csv(csv_path)
            return ApiResponse(HTTPStatus.OK, {"rows": rows})

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
                except json.JSONDecodeError:
                    row["experiment"] = ""
                    row["dataset_version"] = ""
            rows.append(row)

        rows.sort(key=lambda x: x["run_id"], reverse=True)
        return rows

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
