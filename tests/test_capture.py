"""Synthetic on-disk capture/store tests. These do not measure RF performance."""
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sqlite3
import struct
import tempfile
import threading
import unittest
from unittest.mock import patch

from cyt_core import Observation, Rules, summarize
from cyt_core.kismet import ingest
from cyt_core.store import Store
from cyt_core.wifi import SkipFrame, decode


def frame(ssid=b"", *, control=0x40, mac="02:00:00:00:00:01"):
    header = struct.pack("<HH", control, 0) + b"\xff" * 6 + bytes.fromhex(mac.replace(":", "")) + b"\xff" * 6 + b"\0\0"
    if control & 0x0c == 8:
        return header
    return header + (b"\0" * 12 if control == 0x80 else b"") + bytes([0, len(ssid)]) + ssid


def capture(path, rows=(), version=11):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE KISMET (db_version INTEGER)")
    db.execute("INSERT INTO KISMET VALUES (?)", (version,))
    db.execute("CREATE TABLE packets (ts_sec INT, ts_usec INT, dlt INT, packet BLOB, signal INT, error INT, phyname TEXT)")
    db.executemany("INSERT INTO packets VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    db.commit()
    return db


def row(timestamp=1000, packet=None, **changes):
    values = dict(ts_sec=timestamp, ts_usec=0, dlt=105, packet=frame() if packet is None else packet,
                  signal=-45, error=0, phyname="IEEE802.11")
    values.update(changes)
    return tuple(values.values())


class FrameTests(unittest.TestCase):
    def test_wildcard_named_and_binary_ssids(self):
        for ssid in (b"", b"Alice's WiFi", b"\xff\xfe"):
            with self.subTest(ssid=ssid):
                result = decode(frame(ssid), 105)
                self.assertEqual(result["ssid_hex"], ssid.hex())
                self.assertEqual(result["kind"], "probe")
        self.assertIsNone(decode(frame(b"\xff"), 105)["ssid"])

    def test_data_uses_transmitter_even_from_distribution_system(self):
        result = decode(frame(control=0x0208), 105)
        self.assertEqual(result["address"], "02:00:00:00:00:01")
        self.assertEqual(result["kind"], "data_header")
        self.assertNotIn("ssid", result)

    def test_beacon_is_not_a_directed_probe(self):
        fields = decode(frame(b"AP", control=0x80), 105)
        event = Observation("run", "pi", "wifi", observed_at=1000, **fields)
        self.assertEqual(summarize([event], at=1000)["results"][0]["directed_ssids"], [])

    def test_radiotap_fcs_and_extended_alignment(self):
        basic = struct.pack("<BBHI", 0, 0, 9, 2) + b"\x10"
        self.assertEqual(decode(basic + frame() + b"1234", 127)["ssid"], "")
        extended = struct.pack("<BBHII", 0, 0, 25, 0x80000003, 0) + b"\0" * 12 + b"\0"
        self.assertEqual(decode(extended + frame(), 127)["kind"], "probe")
        with self.assertRaisesRegex(SkipFrame, "bad_fcs"):
            decode(basic[:-1] + b"\x40" + frame(), 127)

    def test_malformed_frames_do_not_produce_sightings(self):
        cases = [(b"", 105), (frame(), 1), (frame()[:20], 105), (frame() + b"\x01", 105),
                 (frame(b"a")[:-1], 105), (frame(b"a" * 33), 105), (frame() + b"\0\0", 105),
                 (frame(mac="ff:ff:ff:ff:ff:ff"), 105), (frame(control=0x4808), 105),
                 (b"\0\0\xff\xff" + b"\0" * 8, 127)]
        # The QoS case needs two extra header bytes and must be rejected.
        cases[-2] = (frame(control=0x0088), 105)
        for packet, dlt in cases:
            with self.subTest(packet=packet, dlt=dlt), self.assertRaises(SkipFrame):
                decode(packet, dlt)


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / "capture #1.kismet"
        self.target = self.root / "cyt.sqlite3"
        self.writer = capture(self.source, [row(t) for t in (1000, 1100, 1200)])
        self.addCleanup(self.writer.close)
        self.store = Store(self.target)
        self.addCleanup(self.store.db.close)

    def ingest(self, path=None, **kwargs):
        return ingest(path or self.source, self.store, session="run", observer="pi", **kwargs)

    def test_restart_and_duplicate_poll_do_not_invent_recurrence(self):
        self.assertEqual(self.ingest(batch_size=1)["inserted"], 1)
        self.store.db.close()
        self.store = Store(self.target)
        self.addCleanup(self.store.db.close)
        self.assertEqual(self.ingest()["inserted"], 2)
        self.assertEqual(self.ingest()["inserted"], 0)
        report = self.store.report(at=1200, rules=Rules())
        self.assertEqual(report["results"][0]["observations"], 3)
        self.assertEqual(report["results"][0]["state"], "recurring")
        self.assertEqual(report["results"][0]["distinct_observer_locations"], 0)

    def test_live_wal_append_and_original_timestamps(self):
        self.writer.execute("PRAGMA journal_mode=WAL")
        self.ingest()
        self.writer.execute("INSERT INTO packets VALUES (?, ?, ?, ?, ?, ?, ?)", row(1300))
        self.writer.commit()
        self.assertEqual(self.ingest()["inserted"], 1)
        self.assertEqual(self.store.status()["newest_observed_at"], 1300)

    def test_renamed_copy_does_not_duplicate_events(self):
        self.ingest()
        other = self.root / "copy.kismet"
        shutil.copyfile(self.source, other)
        self.assertEqual(self.ingest(other)["inserted"], 0)
        self.assertEqual(self.store.status()["observations"], 3)

    def test_rotated_new_file_starts_from_first_packet(self):
        self.ingest()
        rotated = self.root / "new.kismet"
        capture(rotated, [row(1300)]).close()
        self.assertEqual(self.ingest(rotated)["inserted"], 1)
        self.assertEqual(len(self.store.status()["sources"]), 2)

    def test_source_file_unchanged_after_reading(self):
        before = self.source.read_bytes()
        self.ingest()
        self.assertEqual(self.source.read_bytes(), before)

    def test_failed_batch_rolls_back_events_and_checkpoint(self):
        original = self.store.insert
        calls = 0

        def interrupted(event):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("simulated interruption")
            return original(event)

        with patch.object(self.store, "insert", interrupted), self.assertRaises(RuntimeError):
            self.ingest()
        self.assertEqual(self.store.status()["observations"], 0)
        self.assertEqual(self.store.status()["sources"], [])
        self.assertEqual(self.ingest()["inserted"], 3)

    def test_rewritten_checkpoint_fails_without_silent_recount(self):
        self.ingest()
        self.writer.execute("UPDATE packets SET signal=-60 WHERE rowid=3")
        self.writer.commit()
        with self.assertRaisesRegex(ValueError, "rewritten"):
            self.ingest()
        self.assertEqual(self.store.status()["observations"], 3)

    def test_skip_reasons_and_same_timestamp_distinct_events(self):
        self.writer.executemany("INSERT INTO packets VALUES (?, ?, ?, ?, ?, ?, ?)",
                                [row(1200, packet=frame(b"different")), row(1300, error=1),
                                 row(1300, dlt=1), row(1300, ts_usec=1000000), row(1300, phyname="Bluetooth")])
        self.writer.commit()
        result = self.ingest()
        self.assertEqual(result["inserted"], 4)
        self.assertEqual(sum(result["skipped"].values()), 4)
        self.assertEqual(self.ingest()["rows_read"], 0)

    def test_retention_preserves_checkpoints(self):
        self.store.max_events = 2
        self.assertEqual(self.ingest()["removed"], 1)
        self.assertEqual(self.store.status()["observations"], 2)
        with self.store.db:
            self.assertEqual(self.store.trim(1200), 1)
        self.assertEqual(self.ingest()["inserted"], 0)
        self.assertEqual(self.store.status()["observations"], 1)

    def test_known_list_persists_normalizes_and_reloads(self):
        self.ingest()
        self.store.known("add", "wifi", "02:00:00:00:00:01", "my test radio")
        self.assertEqual(self.store.report(at=1200, rules=Rules())["observed_identifiers"], 0)
        self.store.known("remove", "wifi", "02:00:00:00:00:01")
        self.assertEqual(self.store.report(at=1200, rules=Rules())["observed_identifiers"], 1)

    def test_event_time_window_and_future_exclusion(self):
        self.ingest()
        result = self.store.report(at=1150, rules=Rules(window_seconds=100))
        self.assertEqual(result["results"][0]["first_observed_at"], 1100)
        self.assertEqual(result["results"][0]["observations"], 1)

    def test_empty_unknown_version_missing_file_and_wrong_destination(self):
        empty = self.root / "empty.kismet"
        capture(empty).close()
        self.assertEqual(self.ingest(empty)["state"], "empty_capture")
        old = self.root / "old.kismet"
        capture(old, version=5).close()
        with self.assertRaisesRegex(ValueError, "v11"):
            self.ingest(old)
        with self.assertRaises(sqlite3.Error):
            self.ingest(self.root / "absent.kismet")
        self.assertFalse((self.root / "absent.kismet").exists())
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "CYT store"):
            Store(self.source)
        self.assertEqual(before, self.source.read_bytes())

    def test_health_distinguishes_empty_stale_recent_and_clock_error(self):
        self.assertEqual(self.store.status(at=1200)["state"], "empty")
        self.ingest()
        for at, expected in ((1200, "recent_observations"), (1500, "stale"), (1000, "clock_ahead")):
            self.assertEqual(self.store.status(at=at)["state"], expected)

    def test_event_identity_rejects_conflicts_but_accepts_distinct_same_time_frames(self):
        event = Observation("run", "pi", "wifi", "02:00:00:00:00:01", 1000, "probe", ssid="", source_id="capture", event_id="1")
        with self.store.db:
            self.assertEqual(self.store.insert(event), 1)
            self.assertEqual(self.store.insert(event), 0)
            self.assertEqual(self.store.insert(replace(event, event_id="2")), 1)
            with self.assertRaisesRegex(ValueError, "conflicting"):
                self.store.insert(replace(event, ssid="changed"))

    def test_concurrent_collectors_do_not_double_count_or_rewind(self):
        barrier = threading.Barrier(2)
        results, failures = [], []

        def run():
            try:
                with Store(self.target) as store:
                    barrier.wait(timeout=5)
                    results.append(ingest(self.source, store, session="run", observer="pi")["inserted"])
            except Exception as error:
                failures.append(error)

        threads = [threading.Thread(target=run) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(10)
        self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual(failures, [])
        self.assertEqual(sorted(results), [0, 3])
        self.assertEqual(self.store.status()["observations"], 3)
