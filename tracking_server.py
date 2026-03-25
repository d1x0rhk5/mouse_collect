from __future__ import annotations

import argparse
import errno
import json
import os
import threading
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_RECENT_LIMIT = 200
MAX_RECENT_EVENTS = 5000


class GetterStore:
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._recent: deque[dict[str, Any]] = deque(maxlen=MAX_RECENT_EVENTS)
        self._total = 0

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def append(self, payload: Any, client_ip: str) -> int:
        if isinstance(payload, list):
            candidates = payload
        else:
            candidates = [payload]

        accepted = 0
        lines: list[str] = []
        records: list[dict[str, Any]] = []

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            record = {
                "received_at": self._now_iso(),
                "client_ip": client_ip,
                "payload": candidate,
            }
            records.append(record)
            lines.append(json.dumps(record, ensure_ascii=False))
            accepted += 1

        if not accepted:
            return 0

        with self._lock:
            with self.output_path.open("a", encoding="utf-8") as handle:
                handle.write("\n".join(lines) + "\n")

            for record in records:
                self._recent.append(record)

            self._total += accepted

        return accepted

    def snapshot(self, limit: int = DEFAULT_RECENT_LIMIT) -> dict[str, Any]:
        bounded_limit = max(1, min(limit, MAX_RECENT_EVENTS))
        with self._lock:
            recent = list(self._recent)[-bounded_limit:]
            total = self._total

        return {
            "total_events": total,
            "recent_limit": bounded_limit,
            "recent_events": recent,
            "log_path": str(self.output_path),
        }

    def clear(self) -> None:
        with self._lock:
            self._recent.clear()
            self._total = 0
            self.output_path.write_text("", encoding="utf-8")


STORE = GetterStore(ROOT / "logs" / "getter_events.ndjson")


class TrackingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class TrackingRequestHandler(SimpleHTTPRequestHandler):
    server_version = "WebArenaTrackingServer/1.0"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def copyfile(self, source, outputfile) -> None:
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Browsers routinely cancel in-flight asset requests during
            # navigation; that should not spam the terminal with tracebacks.
            return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self) -> None:
        if self._parsed_path().path != "/getter":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_POST(self) -> None:
        parsed = self._parsed_path()

        if parsed.path != "/getter":
            self._discard_request_body()
            self._redirect_after_post(parsed.path)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as error:
            self._write_json(
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid_json", "detail": str(error)},
            )
            return

        accepted = STORE.append(payload, self.client_address[0])
        self._write_json(
            HTTPStatus.ACCEPTED,
            {
                "accepted": accepted,
                "total_events": STORE.snapshot(limit=1)["total_events"],
            },
        )

    def do_GET(self) -> None:
        parsed = self._parsed_path()

        if parsed.path == "/getter":
            query = parse_qs(parsed.query)
            limit = DEFAULT_RECENT_LIMIT
            raw_limit = query.get("limit", [str(DEFAULT_RECENT_LIMIT)])[0]
            if raw_limit.isdigit():
                limit = int(raw_limit)

            if query.get("format", ["json"])[0] == "ndjson":
                self._write_ndjson()
                return

            self._write_json(HTTPStatus.OK, STORE.snapshot(limit=limit))
            return

        super().do_GET()

    def do_HEAD(self) -> None:
        parsed = self._parsed_path()

        if parsed.path == "/getter":
            query = parse_qs(parsed.query)
            if query.get("format", ["json"])[0] == "ndjson":
                body = STORE.output_path.read_text(encoding="utf-8") if STORE.output_path.exists() else ""
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
                self.send_header("Content-Length", str(len(body.encode("utf-8"))))
                self.end_headers()
                return

            body = json.dumps(STORE.snapshot(limit=1), ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return

        super().do_HEAD()

    def do_DELETE(self) -> None:
        if self._parsed_path().path != "/getter":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
            return

        STORE.clear()
        self._write_json(HTTPStatus.OK, {"status": "cleared"})

    def _parsed_path(self):
        return urlparse(self.path)

    def _write_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def _write_ndjson(self) -> None:
        body = STORE.output_path.read_text(encoding="utf-8") if STORE.output_path.exists() else ""
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def _discard_request_body(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > 0:
            self.rfile.read(content_length)

    def _normalized_path(self, path: str) -> str:
        cleaned = path.rstrip("/")
        return cleaned or "/"

    def _redirect_after_post(self, path: str) -> None:
        normalized = self._normalized_path(path)
        location = self._post_redirect_target(normalized)
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _post_redirect_target(self, normalized_path: str) -> str:
        if normalized_path == "/reddit/login":
            return "/reddit/"
        if normalized_path == "/reddit/registration":
            return "/reddit/login/"
        if normalized_path == "/reddit/reset_password":
            return "/reddit/login/"
        if normalized_path == "/shopping/customer/account/login":
            return "/shopping/customer/account/"
        if normalized_path == "/shopping/customer/account/create":
            return "/shopping/customer/account/"
        if normalized_path == "/shopping/customer/account/forgotpassword":
            return "/shopping/customer/account/login/"
        if normalized_path.startswith("/shopping/checkout/cart/add"):
            return "/shopping/checkout/cart/"
        if normalized_path.startswith("/shopping/wishlist/index/add"):
            return "/shopping/wishlist/"
        if normalized_path == "/shopping":
            return "/shopping/"
        if normalized_path == "/reddit":
            return self.headers.get("Referer") or "/reddit/"
        if normalized_path.startswith("/shopping/"):
            return self.headers.get("Referer") or f"{normalized_path}/"
        if normalized_path.startswith("/reddit/"):
            return self.headers.get("Referer") or f"{normalized_path}/"
        return self.headers.get("Referer") or "/"

    def log_message(self, format: str, *args: Any) -> None:
        # Hidden/background launches on Windows can stall when the request
        # handler writes to an unavailable console during send_response().
        # Keeping this quiet avoids hanging the HTTP response path.
        return


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve the local WebArena mirror and collect tracking events.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind host. Default: {DEFAULT_HOST}")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Bind port. Default: {DEFAULT_PORT}")
    return parser.parse_args()


def run_server(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
    try:
        server = TrackingHTTPServer((host, port), TrackingRequestHandler)
    except OSError as error:
        if error.errno in {errno.EADDRINUSE, 10048}:
            raise SystemExit(
                f"Port {port} is already in use. Stop the other server or run with a different port, "
                f"for example: python webarena.py serve --port {port + 1}"
            ) from None
        raise
    if os.environ.get("WEBARENA_TRACKING_VERBOSE") == "1":
        print(f"Tracking server: http://{host}:{port}/")
        print(f"Getter endpoint: http://{host}:{port}/getter")
        print(f"Log file: {STORE.output_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping tracking server.")
    finally:
        server.server_close()


def main() -> None:
    args = parse_args()
    run_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
