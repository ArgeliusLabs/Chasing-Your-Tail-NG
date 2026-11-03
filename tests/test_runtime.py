"""CLI lifecycle and read-only HTTP contract tests using temporary stores."""
import http.client
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from cyt_core.store import Store
from cyt_core.web import make_server
from test_capture import capture, row

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "store.sqlite3"

    def run_cli(self, *args, code=0):
        process = subprocess.run([sys.executable, "-B", "-m", "cyt_core", *map(str, args)],
                                 cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(process.returncode, code, process.stderr)
        return process

    def test_cli_ingest_restart_report_known_and_export(self):
        source = self.root / "test.kismet"
        capture(source, [row(t) for t in (1000, 1100, 1200)]).close()
        args = ["ingest", source, "--db", self.db, "--session", "trip", "--observer", "pi", "--batch-size", "1"]
        self.run_cli(*args)
        rerun = self.run_cli(*args)
        self.assertEqual(json.loads(rerun.stdout)["inserted"], 0)
        report_args = ["report", "--db", self.db, "--at", "1200", "--window-seconds", "1200"]
        result = json.loads(self.run_cli(*report_args).stdout)
        self.assertEqual(result["results"][0]["state"], "recurring")
        self.run_cli("known", "add", "--db", self.db, "--protocol", "wifi", "--address", "02:00:00:00:00:01")
        self.assertEqual(json.loads(self.run_cli(*report_args).stdout)["observed_identifiers"], 0)
        exported = self.run_cli("export", "--db", self.db)
        self.assertEqual(len(exported.stdout.splitlines()), 3)
        self.assertTrue(all("packet" not in json.loads(line) for line in exported.stdout.splitlines()))

    def test_bad_jsonl_rolls_back_entire_import(self):
        source = self.root / "bad.jsonl"
        fixture = (ROOT / "research/example-route.jsonl").read_text(encoding="utf-8")
        source.write_text(fixture + "\n{broken\n", encoding="utf-8")
        self.assertIn("line", self.run_cli("import-jsonl", source, "--db", self.db, code=2).stderr)
        status = json.loads(self.run_cli("status", "--db", self.db).stdout)
        self.assertEqual(status["observations"], 0)

    def test_same_source_and_destination_rejected_without_write(self):
        source = self.root / "test.kismet"
        capture(source, [row()]).close()
        before = source.read_bytes()
        self.run_cli("ingest", source, "--db", source, "--session", "trip", "--observer", "pi", code=2)
        self.assertEqual(before, source.read_bytes())

    def test_missing_capture_and_invalid_options_fail(self):
        self.run_cli("ingest", self.root / "missing*", "--db", self.db,
                     "--session", "trip", "--observer", "pi", code=2)
        self.run_cli("known", "add", "--db", self.db, code=2)
        self.run_cli("report", "--db", self.db, "--window-seconds", "nan", code=2)
        self.run_cli("ingest", self.root / "missing*", "--db", self.db, "--session", "trip",
                     "--observer", "pi", "--follow", "--batch-size", "0", code=2)

    def test_follow_discovers_new_rotated_files_without_recounting(self):
        source = self.root / "1.kismet"
        now = int(time.time())
        capture(source, [row(now)]).close()
        with subprocess.Popen([sys.executable, "-B", "-m", "cyt_core", "ingest", str(self.root / "*.kismet"),
                               "--db", str(self.db), "--session", "trip", "--observer", "pi",
                               "--follow", "--poll-seconds", ".1"], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True) as process:
            try:
                deadline = time.monotonic() + 5
                while not self.db.exists() and time.monotonic() < deadline:
                    time.sleep(.05)
                capture(self.root / "2.kismet", [row(now + 1)]).close()
                count = 0
                while time.monotonic() < deadline:
                    with Store(self.db) as store:
                        count = store.status()["observations"]
                    if count == 2:
                        break
                    time.sleep(.05)
                self.assertEqual(count, 2)
                time.sleep(.2)
                with Store(self.db) as store:
                    self.assertEqual(store.status()["observations"], 2)
            finally:
                process.terminate()
                process.wait(timeout=5)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "cyt.sqlite3"
        self.ready = threading.Event()
        self.stop = threading.Event()

        def run():
            with Store(self.db) as store, make_server(store, 0) as server:
                self.port = server.server_port
                self.ready.set()
                while not self.stop.is_set():
                    server.handle_request()

        self.thread = threading.Thread(target=run, daemon=True)
        self.thread.start()
        self.assertTrue(self.ready.wait(5))
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.stop.set()
        self.thread.join(5)
        self.assertFalse(self.thread.is_alive())

    def request(self, path, method="GET", headers=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        return response.status, dict(response.getheaders()), response.read()

    def test_assets_and_empty_report_are_served_without_external_dependencies(self):
        for path in ("/", "/app.js", "/style.css", "/api/report?window=1200"):
            status, headers, body = self.request(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers["Cache-Control"], "no-store")
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            self.assertTrue(body)
        report = json.loads(body)
        self.assertEqual(report["storage"]["state"], "empty")
        self.assertEqual(report["storage"]["coverage"], "unknown")

    def test_rebinding_cross_origin_mutation_and_path_traversal_rejected(self):
        self.assertEqual(self.request("/api/report", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("/api/report", headers={"Origin": "https://evil.example"})[0], 403)
        self.assertEqual(self.request("/api/report", method="POST")[0], 501)
        self.assertEqual(self.request("/../model.py")[0], 404)

    def test_invalid_or_oversized_windows_fail(self):
        for query in ("window=nan", "window=-1", "window=999999", "window=60&window=120", "at=1000"):
            self.assertEqual(self.request("/api/report?" + query)[0], 400)
