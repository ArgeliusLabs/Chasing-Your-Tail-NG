"""One-hour synthetic software soak; no radios, networks, or personal data."""
import argparse
import json
from pathlib import Path
import sqlite3
import statistics
import struct
import sys
import time
import tracemalloc

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cyt_core.kismet import ingest
from cyt_core.model import Rules
from cyt_core.store import Store

parser = argparse.ArgumentParser()
parser.add_argument("--seconds", type=int, default=3600)
parser.add_argument("--output", required=True, type=Path, help="new directory for synthetic captures and results")
args = parser.parse_args()
if args.seconds < 1:
    parser.error("--seconds must be positive")
folder = args.output
folder.mkdir(exist_ok=False)
started = time.time()
start = time.monotonic()
tracemalloc.start()
target = folder / "cyt.sqlite3"
store = Store(target, max_events=5000)
sources = []
writer = None
iterations = written = inserted = removed = restarts = duplicate_checks = 0
timings = []
reports = []
samples = []
try:
    while time.monotonic() - start < args.seconds:
        tick = time.monotonic()
        if iterations % 120 == 0:
            if writer is not None:
                writer.close()
            path = folder / f"capture-{len(sources):03}.kismet"
            sources.append(path)
            writer = sqlite3.connect(path)
            writer.execute("PRAGMA journal_mode=WAL")
            writer.execute("CREATE TABLE KISMET(db_version INTEGER)")
            writer.execute("INSERT INTO KISMET VALUES(11)")
            writer.execute("CREATE TABLE packets(ts_sec INT, ts_usec INT, dlt INT, packet BLOB, signal INT, error INT, phyname TEXT)")
        now = time.time()
        second = int(now)
        records = []
        for index in range(100):
            mac = bytes([2, 0, 0, 0, index // 256, index % 256 + 1])
            beacon = index >= 75
            header = struct.pack("<HH", 0x80 if beacon else 0x40, 0) + b"\xff" * 6 + mac + b"\xff" * 6 + b"\0\0"
            ssid = b"" if index < 50 else b"synthetic-soak"
            packet = header + (b"\0" * 12 if beacon else b"") + bytes([0, len(ssid)]) + ssid
            records.append((second, index, 105, packet, -50, 0, "IEEE802.11"))
        writer.executemany("INSERT INTO packets VALUES(?, ?, ?, ?, ?, ?, ?)", records)
        writer.commit()
        written += len(records)
        begin = time.perf_counter()
        for path in sources:
            result = ingest(path, store, session="synthetic-soak", observer="software-fixture", retention_before=now - 90)
            inserted += result["inserted"]
            removed += result.get("removed", 0)
        timings.append(time.perf_counter() - begin)
        if iterations % 30 == 0:
            duplicate = ingest(sources[-1], store, session="synthetic-soak", observer="software-fixture")
            assert duplicate["inserted"] == 0 and duplicate["rows_read"] == 0
            duplicate_checks += 1
            begin = time.perf_counter()
            report = store.report(at=now + 1, rules=Rules(window_seconds=120))
            reports.append(time.perf_counter() - begin)
            assert report["storage"]["observations"] <= 5000
            assert report["observed_identifiers"] <= 100
            del report
        if iterations and iterations % 300 == 0:
            store.db.close()
            store = Store(target, max_events=5000)
            restarts += 1
        if iterations % 60 == 0:
            current, peak = tracemalloc.get_traced_memory()
            sample = {"elapsed_seconds": round(time.monotonic() - start, 2), "written": written,
                      "inserted": inserted, "retained": store.status()["observations"],
                      "capture_files": len(sources), "heap_current_bytes": current,
                      "heap_peak_bytes": peak, "store_bytes": target.stat().st_size}
            samples.append(sample)
            (folder / "progress.json").write_text(json.dumps(sample, indent=2), encoding="utf-8")
            print(json.dumps(sample), flush=True)
        iterations += 1
        time.sleep(max(0, 1 - (time.monotonic() - tick)))
    assert inserted == written, (inserted, written)
    final_count = store.status()["observations"]
    assert final_count <= 5000
    result = {"started_at": started, "ended_at": time.time(), "elapsed_seconds": time.monotonic() - start,
              "iterations": iterations, "records_written": written, "records_inserted": inserted,
              "records_removed": removed, "retained": final_count, "capture_files": len(sources),
              "restart_checks": restarts, "duplicate_checks": duplicate_checks,
              "ingest_pass_median_seconds": statistics.median(timings),
              "ingest_pass_p95_seconds": sorted(timings)[int(.95 * (len(timings) - 1))],
              "report_median_seconds": statistics.median(reports),
              "report_p95_seconds": sorted(reports)[int(.95 * (len(reports) - 1))],
              "traced_heap_peak_bytes": tracemalloc.get_traced_memory()[1],
              "samples": samples, "result": "passed", "hardware_test": False}
    (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "samples"}), flush=True)
finally:
    if writer is not None:
        writer.close()
    store.db.close()
