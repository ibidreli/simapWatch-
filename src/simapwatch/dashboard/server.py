"""Small HTTP server for the dashboard MVP."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from simapwatch.dashboard.service import build_dashboard_payload


STATIC_DIR = Path(__file__).resolve().parent / "static"


def _read_static_file(name: str) -> bytes:
    return (STATIC_DIR / name).read_bytes()


def make_handler(db_path: str):
    class DashboardHandler(BaseHTTPRequestHandler):
        def _send_bytes(self, payload: bytes, content_type: str, status: int = HTTPStatus.OK) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._send_bytes(_read_static_file("index.html"), "text/html; charset=utf-8")
                return
            if parsed.path == "/app.css":
                self._send_bytes(_read_static_file("app.css"), "text/css; charset=utf-8")
                return
            if parsed.path == "/app.js":
                self._send_bytes(_read_static_file("app.js"), "application/javascript; charset=utf-8")
                return
            if parsed.path == "/api/dashboard":
                payload = json.dumps(build_dashboard_payload(db_path), ensure_ascii=False).encode("utf-8")
                self._send_bytes(payload, "application/json; charset=utf-8")
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
