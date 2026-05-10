#!/usr/bin/env python3
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from core import (
    BASE_URL,
    REPORTS_DIR,
    SERVER_PORT,
    SERVER_URL,
    build_report_text,
    compare_days,
    summarize_day,
    write_report,
    write_report_bundle,
)


ROOT = Path(__file__).resolve().parent
INDEX_PATH = ROOT / "index.html"
VENDOR_ROOT = ROOT / "vendor"
SERVER_HOST = os.environ.get("AW_ENHANCED_HOST", "127.0.0.1")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_file(INDEX_PATH, "text/html; charset=utf-8")
            return
        if parsed.path.startswith("/vendor/"):
            asset = (ROOT / parsed.path.lstrip("/")).resolve()
            if VENDOR_ROOT in asset.parents and asset.is_file():
                content_type = "text/plain; charset=utf-8"
                if asset.suffix == ".css":
                    content_type = "text/css; charset=utf-8"
                elif asset.suffix == ".js":
                    content_type = "application/javascript; charset=utf-8"
                self._send_file(asset, content_type)
                return
        if parsed.path.startswith("/reports/"):
            asset = (REPORTS_DIR / parsed.path.removeprefix("/reports/")).resolve()
            if REPORTS_DIR.resolve() in asset.parents and asset.is_file():
                content_type = "application/octet-stream"
                if asset.suffix == ".png":
                    content_type = "image/png"
                elif asset.suffix == ".md":
                    content_type = "text/markdown; charset=utf-8"
                self._send_file(asset, content_type)
                return
        if parsed.path == "/health":
            self._send_json({"ok": True})
            return
        if parsed.path == "/api/day":
            date_str = parse_qs(parsed.query).get("date", [None])[0]
            self._send_json(summarize_day(date_str))
            return
        if parsed.path == "/api/compare":
            query = parse_qs(parsed.query)
            date_str = query.get("date", [None])[0]
            days = int(query.get("days", ["7"])[0])
            self._send_json(compare_days(date_str, days))
            return
        if parsed.path == "/api/report":
            date_str = parse_qs(parsed.query).get("date", [None])[0]
            report_path, summary, copy_ready = write_report(date_str)
            report_text, _ = build_report_text(summary, compare_days(summary["date"]))
            self._send_json(
                {
                    "path": str(report_path),
                    "copy_ready": copy_ready,
                    "markdown": report_text,
                }
            )
            return
        if parsed.path == "/api/report-image":
            date_str = parse_qs(parsed.query).get("date", [None])[0]
            bundle = write_report_bundle(date_str)
            self._send_json(
                {
                    "date": bundle["summary"]["date"],
                    "copy_ready": bundle["copy_ready"],
                    "markdown_path": str(bundle["markdown_path"]),
                    "markdown_url": f'/reports/{bundle["markdown_path"].name}',
                    "image_path": str(bundle["image_path"]),
                    "image_url": f'/reports/{bundle["image_path"].name}',
                    "report_directory": str(REPORTS_DIR.resolve()),
                }
            )
            return
        if parsed.path == "/api/meta":
            self._send_json(
                {
                    "original_dashboard": BASE_URL,
                    "enhanced_dashboard": SERVER_URL,
                    "report_directory": str(REPORTS_DIR.resolve()),
                    "data_source": "Live ActivityWatch buckets from the original Web UI plus browser watcher URL events.",
                }
            )
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def log_message(self, format: str, *args) -> None:
        return

    def _send_json(self, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer((SERVER_HOST, SERVER_PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
