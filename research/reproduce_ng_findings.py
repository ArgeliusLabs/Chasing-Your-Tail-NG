"""Reproduce NG audit findings using synthetic data, without radios or network.

These checks document the behavior of upstream commit 89c88be. They are not
acceptance tests for the replacement. Run from any working directory.
"""
import contextlib
import gc
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from secure_database import SecureKismetDB
from secure_main_logic import SecureCYTMonitor
from surveillance_detector import SurveillanceDetector, load_appearances_from_kismet
from gps_tracker import GPSTracker
from input_validation import InputValidator


def main():
    results = {}
    logging.disable(logging.CRITICAL)
    with tempfile.TemporaryDirectory(prefix="cyt_audit_", dir=ROOT / "research") as temp:
        assert Path(temp).resolve().parent == (ROOT / "research").resolve()
        db_path = str(Path(temp) / "synthetic.kismet")
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE devices(devmac TEXT, last_time REAL, type TEXT, device TEXT)")
        empty = {"dot11.device": {"dot11.device.last_probed_ssid_record": {
            "dot11.probedssid.ssid": "", "dot11.probedssid.last_time": 1000}}}
        conn.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                     ("02:00:00:00:00:01", 1000, "Wi-Fi Client", json.dumps(empty)))
        conn.commit()
        with SecureKismetDB(db_path) as db:
            devices = db.get_devices_by_time_range(900)
            probes = db.get_probe_requests_by_time_range(900)
        assert len(devices) == 1 and probes == []
        results["empty_ssid"] = {"device_rows_retained": len(devices), "probe_rows_returned": len(probes)}

        detector = SurveillanceDetector({})
        load_appearances_from_kismet(db_path, detector)
        assert len(detector.appearances) == 1 and detector.analyze_surveillance_patterns() == []
        load_appearances_from_kismet(db_path, detector)
        assert len(detector.appearances) == 2
        results["summary_loader"] = {"appearances_first_import": 1, "after_reimport_same_row": 2}

        stale = {"dot11.device": {"dot11.device.last_probed_ssid_record": {
            "dot11.probedssid.ssid": "SYNTHETIC_OLD_PROBE", "dot11.probedssid.last_time": 100}}}
        conn.execute("UPDATE devices SET last_time=1000, device=?", (json.dumps(stale),))
        conn.commit()
        with SecureKismetDB(db_path) as db:
            probe = db.get_probe_requests_by_time_range(900)[0]
        assert probe["timestamp"] == 1000
        results["stale_probe"] = {"probe_record_time": 100, "reported_probe_time": probe["timestamp"]}

        stationary = SurveillanceDetector({})
        for timestamp in (1000, 2800, 4600):
            stationary.add_device_appearance("00:00:00:00:00:02", timestamp, "same_place", device_type="Wi-Fi AP")
        scored = stationary.analyze_surveillance_patterns()
        assert scored[0].persistence_score == 1.0 and len(scored[0].locations_seen) == 1
        results["stationary_ap"] = {"score": scored[0].persistence_score, "locations": scored[0].locations_seen}

        no_data_accuracy = SurveillanceDetector({})._generate_analysis_statistics()["detection_accuracy"]
        assert no_data_accuracy == 0.95
        results["empty_dataset_reported_accuracy"] = no_data_accuracy

        # Import under a temporary cwd because upstream configures logging on import.
        previous = Path.cwd()
        try:
            os.chdir(temp)
            with patch("logging.FileHandler", return_value=logging.NullHandler()):
                from surveillance_analyzer import SurveillanceAnalyzer
            analyzer = object.__new__(SurveillanceAnalyzer)
            analyzer.detector = SurveillanceDetector({})
            analyzer.gps_tracker = GPSTracker({})
            with patch("gps_tracker.time.time", return_value=9000):
                analyzer.gps_tracker.add_gps_reading(33.0, -112.0, location_name="Location_1")
                analyzer.gps_tracker.add_gps_reading(34.0, -112.0, location_name="Location_2")
            conn.execute("INSERT INTO devices VALUES (?, ?, ?, ?)",
                         ("02:00:00:00:00:03", 2000, "Wi-Fi Client", "{}"))
            conn.commit()
            analyzer._load_appearances_with_gps(db_path, "Location_1")
            locations = [a.location_id for a in analyzer.detector.appearances]
            assert locations == ["Location_1", "Location_1"]
            assert all(p.timestamp == 9000 for p in analyzer.gps_tracker.locations)
            results["gps_correlation"] = {"device_times": [2000, 1000], "assigned_locations": locations,
                                          "gps_times": [p.timestamp for p in analyzer.gps_tracker.locations]}
        finally:
            os.chdir(previous)
            conn.close()

        output = io.StringIO()
        monitor = SecureCYTMonitor({}, [], [], output)
        monitor.five_ten_min_ago_macs = {"AA:BB:CC:DD:EE:FF"}
        with contextlib.redirect_stdout(io.StringIO()):
            monitor._process_mac_tracking("aa:bb:cc:dd:ee:ff")
        assert output.getvalue() == ""
        results["lowercase_recurrence_missed"] = True

        config = json.loads((ROOT / "config.json").read_text())
        missing = [name for name in config["paths"]["ignore_lists"].values()
                   if not (ROOT / "ignore_lists" / name).exists()]
        assert sorted(missing) == ["mac_list.py", "ssid_list.py"]
        results["configured_ignore_files_missing"] = missing
        assert not InputValidator.validate_ssid("Alice's WiFi")
        results["ordinary_apostrophe_ssid_rejected"] = True
        # Upstream's `with sqlite3.connect(...)` commits but does not close.
        gc.collect()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
