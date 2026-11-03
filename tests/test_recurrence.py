"""Behavior tests for the experimental observation core; no hardware required."""
from dataclasses import replace
import unittest

from cyt_core import Observation, Position, Rules, summarize


def observation(timestamp=1000, **changes):
    values = dict(session="route", observer="pager", protocol="wifi", address="02:00:00:00:00:01",
                  observed_at=timestamp, kind="probe", ssid="")
    values.update(changes)
    return Observation(**values)


def route(**changes):
    return [observation(t, position=Position(33 + i * .01, -112, t, 5), **changes)
            for i, t in enumerate((1000, 1100, 1200))]


class RecurrenceTests(unittest.TestCase):
    def test_wildcard_probes_support_recurrence_without_inventing_ssids(self):
        result = summarize(route(), at=1200)["results"][0]
        self.assertEqual(result["wildcard_probes"], 3)
        self.assertEqual(result["directed_ssids"], [])
        self.assertEqual(result["state"], "recurring_across_locations")

    def test_identical_reimport_does_not_inflate_counts(self):
        events = route()
        result = summarize(events + events, at=1200)
        self.assertEqual(result["results"][0]["observations"], 3)
        self.assertEqual(result["excluded"]["duplicates"], 3)

    def test_unchanged_summary_is_one_observation(self):
        event = observation(kind="device_summary", ssid=None)
        result = summarize([event] * 100, at=1200)["results"][0]
        self.assertEqual(result["state"], "observed")
        self.assertEqual(result["observations"], 1)

    def test_busy_burst_is_not_temporal_recurrence(self):
        result = summarize([observation(1000 + i / 10) for i in range(500)], at=1200)["results"][0]
        self.assertEqual(result["state"], "observed")

    def test_three_bucket_edges_do_not_override_minimum_duration(self):
        result = summarize([observation(t) for t in (1019, 1021, 1081)], at=1200)["results"][0]
        self.assertEqual(result["time_buckets"], 3)
        self.assertEqual(result["state"], "observed")

    def test_stationary_radio_never_gets_route_label(self):
        events = [observation(t, kind="beacon", ssid=None, position=Position(33, -112, t, 5))
                  for t in (1000, 1100, 1200)]
        result = summarize(events, at=1200)["results"][0]
        self.assertEqual(result["state"], "recurring")
        self.assertEqual(result["distinct_observer_locations"], 1)
        self.assertNotIn("threat_score", result)

    def test_missing_gps_does_not_create_locations(self):
        result = summarize([observation(t) for t in (1000, 1100, 1200)], at=1200)["results"][0]
        self.assertEqual(result["distinct_observer_locations"], 0)
        self.assertEqual(result["state"], "recurring")

    def test_stale_poor_or_no_fix_does_not_establish_route(self):
        variants = [dict(measured_at=0), dict(accuracy_m=500), dict(fix_mode=1)]
        for fields in variants:
            with self.subTest(fields=fields):
                events = [replace(e, position=replace(e.position, **fields)) for e in route()]
                self.assertEqual(summarize(events, at=1200)["results"][0]["distinct_observer_locations"], 0)

    def test_jitter_across_grid_boundaries_does_not_establish_route(self):
        events = [observation(t, position=Position(33 + i * .0001, -112, t, 10))
                  for i, t in enumerate((1000, 1100, 1200))]
        self.assertEqual(summarize(events, at=1200)["results"][0]["distinct_observer_locations"], 1)

    def test_zero_coordinates_are_valid_if_fix_is_valid(self):
        event = observation(position=Position(0, 0, 1000, 5))
        self.assertEqual(summarize([event], at=1000)["results"][0]["distinct_observer_locations"], 1)

    def test_mac_rotation_is_not_merged_by_shared_ssid(self):
        events = [observation(t, address=f"02:00:00:00:00:{i:02X}", ssid="Shared WiFi")
                  for i, t in enumerate((1000, 1100, 1200), 1)]
        result = summarize(events, at=1200)
        self.assertEqual(result["observed_identifiers"], 3)
        self.assertTrue(all(r["state"] == "observed" for r in result["results"]))

    def test_sessions_observers_and_protocols_are_separate(self):
        a = observation()
        events = [a, replace(a, session="other"), replace(a, observer="pi"),
                  replace(a, protocol="ble", kind="advertisement", ssid=None, address_type="unknown")]
        self.assertEqual(summarize(events, at=1000)["observed_identifiers"], 4)

    def test_ignore_addresses_are_normalized(self):
        event = observation(address="0a:bb:cc:dd:ee:ff")
        self.assertEqual(summarize([event], at=1000, ignored=[("wifi", "0a:bb:cc:dd:ee:ff")])["results"], [])

    def test_old_and_future_records_are_excluded(self):
        result = summarize([observation(0), observation(3001)], at=3000)
        self.assertEqual(result["observed_identifiers"], 0)
        self.assertEqual(result["excluded"]["outside_window"], 2)

    def test_replay_order_does_not_change_result(self):
        self.assertEqual(summarize(route(), at=1200), summarize(reversed(route()), at=1200))

    def test_conflicting_duplicates_fail_instead_of_silently_overwriting(self):
        with self.assertRaises(ValueError):
            summarize([observation(), observation(ssid="Different")], at=1000)

    def test_ssid_quotes_remain_data(self):
        event = observation(ssid="Alice's WiFi")
        self.assertEqual(summarize([event], at=1000)["results"][0]["directed_ssids"], ["Alice's WiFi"])

    def test_summary_ssid_is_not_reported_as_fresh_probe(self):
        event = observation(kind="device_summary", ssid="Old remembered name")
        self.assertEqual(summarize([event], at=1000)["results"][0]["directed_ssids"], [])

    def test_empty_capture_has_no_accuracy_or_all_clear_claim(self):
        result = summarize([], at=1000)
        self.assertEqual(result["results"], [])
        self.assertNotIn("accuracy", result)
        self.assertIn("coverage is not measured", result["interpretation"])

    def test_invalid_timestamp_and_rule_values_are_rejected(self):
        for value in (float("nan"), float("inf"), True, "1000"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                observation(value)
        with self.assertRaises(ValueError):
            Rules(bucket_seconds=0)

    def test_utf8_length_checked_in_bytes(self):
        with self.assertRaises(ValueError):
            observation(ssid="é" * 17)

    def test_ble_address_type_is_not_inferred_from_wifi_bits(self):
        event = observation(protocol="ble", kind="advertisement", ssid=None)
        self.assertEqual(event.address_type, "unknown")


if __name__ == "__main__":
    unittest.main()
