"""Loopback-only, read-only dashboard. No capture controls or external assets."""
from http.server import BaseHTTPRequestHandler, HTTPServer
from importlib.resources import files
import json
import sqlite3
import time
from urllib.parse import parse_qs, urlsplit

from .model import Rules


def make_server(store, port=8765):
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be between 0 and 65535")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if self.headers.get("Host") != origin.removeprefix("http://") or self.headers.get("Origin", origin) != origin:
                self.send_error(403)
                return
            url = urlsplit(self.path)
            try:
                if url.path == "/api/report":
                    query = parse_qs(url.query)
                    if set(query) - {"window"} or len(query.get("window", [])) > 1:
                        raise ValueError("only one window parameter is supported")
                    window = float(query.get("window", [1200])[0])
                    if not 60 <= window <= 86400:
                        raise ValueError("window must be 60 to 86400 seconds")
                    result = store.report(at=time.time(), rules=Rules(window_seconds=window))
                    body = json.dumps(result, allow_nan=False).encode()
                    content_type = "application/json"
                elif url.path in ("/", "/app.js", "/style.css"):
                    asset, content_type = {"/": ("index.html", "text/html"),
                                           "/app.js": ("app.js", "text/javascript"),
                                           "/style.css": ("style.css", "text/css")}[url.path]
                    body = files("cyt_core").joinpath("static").joinpath(asset).read_bytes()
                else:
                    self.send_error(404)
                    return
            except (ValueError, sqlite3.Error) as error:
                self.reply(400, json.dumps({"error": str(error)}).encode(), "application/json")
                return
            self.reply(200, body, content_type)

        def reply(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    class LocalServer(HTTPServer):
        def get_request(self):
            connection, address = super().get_request()
            connection.settimeout(5)
            return connection, address

    server = LocalServer(("127.0.0.1", port), Handler)
    server.timeout = .5
    return server


def serve(store, *, port=8765):
    import signal
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    previous = signal.signal(signal.SIGTERM, stop)
    try:
        with make_server(store, port) as server:
            print(f"CYT dashboard: http://127.0.0.1:{server.server_port} (read-only)", flush=True)
            while not stopped:
                server.handle_request()
    finally:
        signal.signal(signal.SIGTERM, previous)
