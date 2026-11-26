"""Repeatable synthetic store/report load test for desktop, Pi, or Pager.

Measures this process and dataset only. Python traced allocations are not RSS,
and neither the timings nor the data measure radio performance or battery life.
"""
import argparse
import gc
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cyt_core.model import Observation, Position, Rules
from cyt_core.store import Store


def benchmark(events, identifiers, repeats):
    at = 1700000600
    with tempfile.TemporaryDirectory(prefix="cyt-benchmark-") as directory:
        with Store(Path(directory) / "store.sqlite3", max_events=events) as store:
            started = time.perf_counter()
            with store.db:
                for index in range(events):
                    raw = f"02{index % identifiers:010x}"
                    mac = ":".join(raw[i:i + 2] for i in range(0, 12, 2))
                    timestamp = at - 600 + index * 600 / events
                    location = Position(int((timestamp - at + 600) / 100) * .003, 0, timestamp, 5)
                    store.insert(Observation("synthetic-benchmark", "reference", "wifi", mac,
                                             timestamp, "beacon", ssid="Test", position=location,
                                             source_id="synthetic", event_id=str(index)))
            seed_seconds = time.perf_counter() - started
            durations = []
            result = None
            for _ in range(repeats):
                result = None
                gc.collect()
                started = time.perf_counter()
                result = store.report(at=at, rules=Rules())
                durations.append(time.perf_counter() - started)
                assert result["observed_identifiers"] == identifiers
            result = None
            gc.collect()
            tracemalloc.start()
            result = store.report(at=at, rules=Rules())
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            return {"synthetic": True, "events": events, "identifiers": identifiers,
                    "repeats": repeats, "seed_seconds": seed_seconds,
                    "report_seconds": durations, "report_median_seconds": statistics.median(durations),
                    "report_python_peak_bytes": peak,
                    "store_bytes": (Path(directory) / "store.sqlite3").stat().st_size,
                    "python": platform.python_version(), "platform": platform.platform(),
                    "limitations": "Synthetic desktop/Pi/Pager-local report benchmark; traced Python allocations are not process RSS, and no RF accuracy or battery claim is measured."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--identifiers", type=int, default=100)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    if not 1 <= args.identifiers <= args.events <= 1000000 or not 1 <= args.repeats <= 20:
        parser.error("require 1 <= identifiers <= events <= 1000000 and 1 <= repeats <= 20")
    print(json.dumps(benchmark(args.events, args.identifiers, args.repeats), indent=2))


if __name__ == "__main__":
    main()
