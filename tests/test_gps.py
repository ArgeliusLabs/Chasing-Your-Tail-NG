"""GPS joins must not manufacture route evidence across clocks or fix loss."""
from dataclasses import replace
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cyt_core.gps import geotag, read_gps
from cyt_core.model import Observation, Position

ROOT = Path(__file__).resolve().parents[1]
DEVICE = "/dev/test-gps"


def tpv(timestamp=1000, **changes):
    record = {"class": "TPV", "device": DEVICE, "mode": 3, "lat": 0, "lon": 0,
              "eph": 8, "time": datetime.fromtimestamp(timestamp, timezone.utc).isoformat()}
    record.update(changes)
    return record


def track(*records):
    return read_gps(io.StringIO("\n".join(json.dumps(r) for r in records)), device=DEVICE)


def event(timestamp=1000):
    return Observation("trip", "pi", "wifi", "02:00:00:00:00:01", timestamp, "beacon")


class GPSJoinTests(unittest.TestCase):
    def test_zero_coordinates_and_exact_age_boundary(self):
        gps = track(tpv())
        self.assertEqual(gps.before(1005).latitude, 0)
        self.assertIsNone(gps.before(1005.001))
        self.assertIsNone(gps.before(999.999))

    def test_no_future_fix_or_gap_interpolation(self):
        gps = track(tpv(1000), tpv(1010, lat=1))
        self.assertIsNone(gps.before(1008))
        self.assertEqual(gps.before(1011).latitude, 1)

    def test_timed_loss_of_fix_blocks_recent_good_position(self):
        gps = track(tpv(), tpv(1001, mode=1), tpv(1003, lat=1))
        self.assertIsNotNone(gps.before(1000))
        self.assertIsNone(gps.before(1002))
        self.assertIsNotNone(gps.before(1003))

    def test_untimed_tpv_conservatively_invalidates_previous_epoch(self):
        gps = track(tpv(), {"class": "TPV", "device": DEVICE, "mode": 1}, tpv(1003))
        self.assertIsNone(gps.before(1000))
        self.assertIsNone(gps.before(1002))
        self.assertIsNotNone(gps.before(1003))
        self.assertEqual(gps.stats["untimed_tpv"], 1)

    def test_partial_records_merge_only_in_same_epoch(self):
        first = tpv()
        del first["eph"]
        second = {"class": "TPV", "device": DEVICE, "mode": 3, "time": first["time"], "eph": 5}
        gps = track(first, second, {**second, "time": tpv(1001)["time"]})
        self.assertEqual(gps.before(1000).accuracy_m, 5)
        self.assertIsNone(gps.before(1001))

    def test_same_epoch_fix_loss_clears_coordinates(self):
        gps = track(tpv(), tpv(mode=1), {"class": "TPV", "device": DEVICE, "mode": 3,
                                       "time": tpv()["time"], "eph": 5})
        self.assertIsNone(gps.before(1000))

    def test_horizontal_component_estimates_require_both(self):
        record = tpv(epx=3, epy=4)
        del record["eph"]
        self.assertEqual(track(record).before(1000).accuracy_m, 5)
        del record["epy"]
        self.assertIsNone(track(record).before(1000))

    def test_invalid_fix_or_quality_blocks_old_good_fix(self):
        for changes in ({"eph": 0}, {"eph": -1}, {"eph": 51}, {"eph": float("nan")},
                        {"lat": 91}, {"lon": -181}, {"mode": True}, {"lat": "0"}):
            with self.subTest(changes=changes):
                self.assertIsNone(track(tpv(), tpv(1001, **changes)).before(1001))

    def test_other_receiver_never_contributes_coordinates_or_outages(self):
        gps = track(tpv(), tpv(1001, device="other", mode=1), tpv(1002, device="other", lat=42))
        self.assertEqual(gps.before(1002).latitude, 0)
        with self.assertRaisesRegex(ValueError, "no TPV"):
            track(tpv(device="other"))
        bad = tpv()
        del bad["device"]
        with self.assertRaisesRegex(ValueError, "lacks a device"):
            track(bad)

    def test_ambiguous_time_and_backwards_clock_fail(self):
        for stamp in ("1970-01-01T00:16:40", "bad", 1000, None):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                track(tpv(time=stamp))
        with self.assertRaisesRegex(ValueError, "backwards"):
            track(tpv(1001), tpv(1000))

    def test_malformed_and_oversized_records_fail(self):
        for value in ("{bad", "[]", '{"class":"SKY","blob":"' + "x" * 65536 + '"}'):
            with self.subTest(value=value[:20]), self.assertRaises(ValueError):
                read_gps(io.StringIO(value), device=DEVICE)

    def test_join_preserves_source_identity_and_existing_position(self):
        gps = track(tpv())
        original = replace(event(), source_id="capture", event_id="1")
        already = replace(event(1001), position=Position(1, 1, 1001, 5))
        stats = {}
        joined = list(geotag([original, already, event(1020)], gps, session="trip", observer="pi", stats=stats))
        self.assertEqual(joined[0].event_key, original.event_key)
        self.assertEqual(joined[0].position.latitude, 0)
        self.assertEqual(joined[1], already)
        self.assertIsNone(joined[2].position)
        self.assertEqual(stats, {"observations": 3, "attached": 1, "preserved": 1, "unlocated": 1})

    def test_join_scope_and_quality_options_are_validated(self):
        for args in ({"session": "other"}, {"observer": "other"}, {"max_age": 0}, {"max_accuracy": float("nan")}):
            options = {"session": "trip", "observer": "pi", **args}
            with self.subTest(args=args), self.assertRaises(ValueError):
                list(geotag([event()], track(tpv()), **options))

    def test_cli_export_join_replay_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            raw, gps, output = (folder / name for name in ("raw.jsonl", "gps.jsonl", "located.jsonl"))
            from dataclasses import asdict
            raw.write_text(json.dumps(asdict(event())) + "\n", encoding="utf-8")
            gps.write_text(json.dumps(tpv()) + "\n", encoding="utf-8")
            command = [sys.executable, "-B", "-m", "cyt_core", "geotag", str(raw), "--gps", str(gps),
                       "--gps-device", DEVICE, "--session", "trip", "--observer", "pi", "--output", str(output)]
            run = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads(run.stdout)["join"]["attached"], 1)
            self.assertEqual(json.loads(output.read_text())["position"]["measured_at"], 1000)
            before = output.read_bytes()
            again = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(again.returncode, 2)
            self.assertEqual(output.read_bytes(), before)
            replay = subprocess.run([sys.executable, "-B", "-m", "cyt_core", "replay", str(output),
                                     "--at", "1000"], cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertEqual(json.loads(replay.stdout)["results"][0]["observations_with_usable_position"], 1)
            output.unlink()
            raw.write_text(raw.read_text() + "{bad\n", encoding="utf-8")
            failed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(failed.returncode, 2)
            self.assertFalse(output.exists())
            command[-1] = str(raw)
            same = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=10)
            self.assertEqual(same.returncode, 2)
            self.assertIn("separate", same.stderr)


if __name__ == "__main__":
    unittest.main()
