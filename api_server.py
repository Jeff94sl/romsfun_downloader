#!/usr/bin/env python3
"""
API local (stdlib) para la app de escritorio RomsFun.
Expone JSON + SSE de progreso sin dependencias extra.
"""

import argparse
import json
import os
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(SCRIPT_DIR, ".venv", "bin", "python3")
if os.path.exists(VENV_PYTHON) and sys.executable != VENV_PYTHON and "VIRTUAL_ENV" not in os.environ:
    os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

sys.path.insert(0, SCRIPT_DIR)

from romsfun_core import (  # noqa: E402
    CONSOLE_OPTIONS,
    extract_console_from_url,
    get_console_folder_name,
    list_console_roms,
    normalize_console_slug,
    process_download_batch,
    search_roms,
)
from romsfun_core.catalog import pages_for_limit  # noqa: E402

DEFAULT_PORT = 8765
HOST = "127.0.0.1"

jobs_lock = threading.Lock()
jobs = {}


def json_bytes(data, status=200):
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return status, body, "application/json; charset=utf-8"


class JobState:
    def __init__(self, job_id: str):
        self.id = job_id
        self.events = []
        self.condition = threading.Condition()
        self.done = False
        self.result = None
        self.cancel = False
        self.error = None

    def push(self, event: dict):
        with self.condition:
            self.events.append(event)
            self.condition.notify_all()

    def request_cancel(self):
        self.cancel = True


def run_download_job(job: JobState, payload: dict):
    try:
        items = payload.get("items") or []
        if payload.get("url") and not items:
            url = payload["url"]
            console_name = extract_console_from_url(url) or "ROM"
            title = url.split("/")[-1].replace(".html", "").replace("-", " ").title()
            items = [{"title": title, "console": console_name, "url": url}]

        base_output = payload.get("output") or os.path.join(SCRIPT_DIR, "downloads")
        unzip = payload.get("unzip", True)
        single_version = payload.get("singleVersion", True)
        clean_tags = payload.get("cleanTags", False)

        def on_progress(event):
            job.push(event)

        result = process_download_batch(
            items,
            base_output=base_output,
            unzip=unzip,
            single_version=single_version,
            clean_tags=clean_tags,
            on_progress=on_progress,
            cancel_check=lambda: job.cancel,
        )
        job.result = result
    except Exception as e:
        job.error = str(e)
        job.push({"type": "error", "message": str(e), "trace": traceback.format_exc()})
    finally:
        with job.condition:
            job.done = True
            job.condition.notify_all()


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "RomsFunAPI/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("[api] " + (fmt % args) + "\n")

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send(self, status, body, content_type):
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data, status=200):
        status, body, ctype = json_bytes(data, status)
        self._send(status, body, ctype)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)

        try:
            if path == "/api/health":
                self._send_json({"ok": True, "service": "romsfun-api"})
                return

            if path == "/api/consoles":
                # Deduplicar por slug
                seen = set()
                consoles = []
                for c in CONSOLE_OPTIONS:
                    if c["slug"] not in seen:
                        seen.add(c["slug"])
                        consoles.append(c)
                self._send_json({"consoles": consoles})
                return

            if path == "/api/search":
                query = (qs.get("q") or [""])[0].strip()
                if not query:
                    self._send_json({"error": "Parámetro q requerido"}, 400)
                    return
                results = search_roms(query)
                self._send_json({"results": results, "count": len(results)})
                return

            if path.startswith("/api/console/"):
                slug = path[len("/api/console/") :]
                limit = int((qs.get("limit") or ["20"])[0])
                pages = pages_for_limit(limit)
                results = list_console_roms(
                    normalize_console_slug(slug),
                    max_pages=pages,
                    target_count=limit,
                )
                results = results[:limit]
                self._send_json(
                    {
                        "console": get_console_folder_name(slug),
                        "slug": normalize_console_slug(slug),
                        "results": results,
                        "count": len(results),
                    }
                )
                return

            if path.startswith("/api/jobs/") and path.endswith("/events"):
                job_id = path[len("/api/jobs/") : -len("/events")]
                self._stream_job_events(job_id)
                return

            if path.startswith("/api/jobs/"):
                job_id = path[len("/api/jobs/") :]
                with jobs_lock:
                    job = jobs.get(job_id)
                if not job:
                    self._send_json({"error": "Job no encontrado"}, 404)
                    return
                self._send_json(
                    {
                        "id": job.id,
                        "done": job.done,
                        "error": job.error,
                        "result": job.result,
                    }
                )
                return

            self._send_json({"error": "Not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        try:
            if path == "/api/download":
                payload = self._read_json()
                job_id = str(uuid.uuid4())
                job = JobState(job_id)
                with jobs_lock:
                    jobs[job_id] = job
                thread = threading.Thread(
                    target=run_download_job,
                    args=(job, payload),
                    daemon=True,
                )
                thread.start()
                self._send_json({"jobId": job_id}, 202)
                return

            if path.startswith("/api/jobs/") and path.endswith("/cancel"):
                job_id = path[len("/api/jobs/") : -len("/cancel")]
                with jobs_lock:
                    job = jobs.get(job_id)
                if not job:
                    self._send_json({"error": "Job no encontrado"}, 404)
                    return
                job.request_cancel()
                self._send_json({"ok": True, "cancelled": True})
                return

            self._send_json({"error": "Not found"}, 404)
        except Exception as e:
            self._send_json({"error": str(e), "trace": traceback.format_exc()}, 500)

    def _stream_job_events(self, job_id: str):
        with jobs_lock:
            job = jobs.get(job_id)
        if not job:
            self._send_json({"error": "Job no encontrado"}, 404)
            return

        self.send_response(200)
        self._cors()
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        index = 0
        try:
            while True:
                with job.condition:
                    while index >= len(job.events) and not job.done:
                        job.condition.wait(timeout=15)
                        # keep-alive comment
                        try:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                        except BrokenPipeError:
                            return

                    while index < len(job.events):
                        event = job.events[index]
                        index += 1
                        data = json.dumps(event, ensure_ascii=False)
                        chunk = f"data: {data}\n\n".encode("utf-8")
                        self.wfile.write(chunk)
                        self.wfile.flush()

                    if job.done and index >= len(job.events):
                        break
        except (BrokenPipeError, ConnectionResetError):
            return


def main():
    parser = argparse.ArgumentParser(description="API local RomsFun Desktop")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), ApiHandler)
    print(f"RomsFun API listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
