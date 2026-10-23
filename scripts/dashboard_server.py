#!/usr/bin/env python3
"""Small read-only server for the artifact-backed MedRoute dashboard."""
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / "dashboard"), **kwargs)

    def respond_json(self, value):
        body = json.dumps(value).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/api/runs":
            runs = sorted((p.name for p in ARTIFACTS.iterdir() if p.is_dir()), reverse=True)
            return self.respond_json({"runs": runs})
        if path.startswith("/api/run/"):
            run = unquote(path.removeprefix("/api/run/"))
            folder = (ARTIFACTS / run).resolve()
            if folder.parent != ARTIFACTS.resolve() or not folder.is_dir():
                return self.send_error(404)
            def read(name):
                file = folder / name
                try:
                    return json.loads(file.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    return None
            return self.respond_json({"summary": read("summary.json"),
                "analytical": read("analytical.json"), "config": read("config.json"),
                "measurements": read("measurements.json"),
                "files": sorted(p.name for p in folder.iterdir() if p.is_file())})
        if path.startswith("/artifact/"):
            parts = [unquote(x) for x in path.removeprefix("/artifact/").split("/", 1)]
            if len(parts) == 2:
                target = (ARTIFACTS / parts[0] / parts[1]).resolve()
                if target.parent == (ARTIFACTS / parts[0]).resolve() and target.is_file():
                    return self.send_response_file(target)
            return self.send_error(404)
        return super().do_GET()

    def send_response_file(self, target):
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print("MedRoute dashboard: http://127.0.0.1:8765")
    ThreadingHTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
