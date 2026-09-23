"""Local webhook receiver used to show Alertmanager notifications in container logs."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class AlertHandler(BaseHTTPRequestHandler):
    """Accept Alertmanager webhooks and log their structured payload."""

    def do_POST(self) -> None:  # noqa: N802 - method name is defined by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        print(json.dumps(payload, indent=2, sort_keys=True), flush=True)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"accepted")

    def log_message(self, format: str, *args: object) -> None:
        print(f"alert-sink: {format % args}", flush=True)


if __name__ == "__main__":
    host = os.getenv("ALERT_SINK_HOST", "127.0.0.1")
    ThreadingHTTPServer((host, 5001), AlertHandler).serve_forever()
