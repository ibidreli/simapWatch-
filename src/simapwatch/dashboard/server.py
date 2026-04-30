"""Small HTTP server for the dashboard."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from simapwatch.dashboard.service import build_dashboard_filter_options, build_dashboard_payload


STATIC_DIR = Path(__file__).resolve().parent / "static"


def _read_static_file(name: str) -> bytes:
    return (STATIC_DIR / name).read_bytes()


def _first_param(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _bounded_int(value: str | None, *, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(parsed, maximum))


def make_handler(db_path: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send_bytes(self, payload: bytes, content_type: str, status: int = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_json(self, payload: dict[str, object], status: int = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(body, "application/json; charset=utf-8", status=status)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            query = parse_qs(parsed.query)

            if parsed.path == "/":
                self._send_bytes(_read_static_file("index.html"), "text/html; charset=utf-8")
                return
            if parsed.path == "/app.css":
                self._send_bytes(_read_static_file("app.css"), "text/css; charset=utf-8")
                return
            if parsed.path in {"/dashboard.js", "/app.js"}:
                self._send_bytes(_read_static_file("dashboard.js"), "application/javascript; charset=utf-8")
                return
            if parsed.path == "/api/dashboard":
                filters = {
                    "from": _first_param(query, "from"),
                    "to": _first_param(query, "to"),
                    "buyer": _first_param(query, "buyer"),
                    "winner": _first_param(query, "winner"),
                    "cpv": _first_param(query, "cpv"),
                    "procurement_type": _first_param(query, "procurement_type"),
                    "text": _first_param(query, "text"),
                    "min_amount": _first_param(query, "min_amount"),
                    "max_amount": _first_param(query, "max_amount"),
                }
                payload = build_dashboard_payload(
                    db_path,
                    filters=filters,
                    top_n=_bounded_int(_first_param(query, "top_n"), default=8, minimum=3, maximum=20),
                    recent_limit=_bounded_int(_first_param(query, "recent_limit"), default=12, minimum=5, maximum=100),
                    map_limit=_bounded_int(_first_param(query, "map_limit"), default=150, minimum=20, maximum=500),
                    months=_bounded_int(_first_param(query, "months"), default=12, minimum=3, maximum=36),
                )
                self._send_json(payload)
                return
            if parsed.path == "/api/dashboard/options":
                limit = _bounded_int(_first_param(query, "limit"), default=250, minimum=50, maximum=700)
                payload = build_dashboard_filter_options(db_path, limit=limit)
                self._send_json(payload)
                return
            if parsed.path == "/health":
                self._send_bytes(b"ok", "text/plain; charset=utf-8")
                return

            self._send_bytes(b"not found", "text/plain; charset=utf-8", status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return DashboardHandler


def serve_dashboard(db_path: str, host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(db_path))
    print(f"dashboard listening on http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
