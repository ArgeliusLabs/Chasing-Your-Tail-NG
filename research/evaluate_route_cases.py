"""Synthetic counterexamples: what recurrence can and cannot establish.

Run from any directory. These are software policy checks, not RF accuracy data.
The scenario truth is deliberately kept outside the observations given to CYT.
"""
from dataclasses import replace
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cyt_core.model import Observation, Position
from cyt_core.recurrence import summarize


def cases():
    route = [Observation("synthetic-route", "pi", "wifi", "02:00:00:00:00:01",
                         t, "beacon", ssid="Test hotspot",
                         position=Position(i * .003, 0, t, 5))
             for i, t in enumerate((1000, 1100, 1200))]
    across = ["recurring_across_locations"]
    return [
        ("persistent_hotspot", route, across,
         "A persistent advertised address can supply route recurrence."),
        ("consenting_companion", route, across,
         "A companion and a follower can supply identical observations; intent is not observable."),
        ("fixed_ap_heard_across_route", route, across,
         "Three observer positions do not establish transmitter movement."),
        ("stable_wildcard_probes", [replace(e, kind="probe", ssid="") for e in route], across,
         "Remembered network names are not necessary when an address persists."),
        ("rotating_phone", [replace(e, address=f"02:00:00:00:01:{i:02x}", kind="probe", ssid="")
                            for i, e in enumerate(route)], ["observed"] * 3,
         "An address change breaks continuity; the program does not join it by guessed identity."),
        ("silent_follower", [], [],
         "A nearby person who emits no captured frames is unobservable."),
        ("stationary_observer", [replace(e, position=Position(0, 0, e.observed_at, 5)) for e in route],
         ["recurring"], "Time alone can show recurrence but cannot show route persistence."),
        ("gps_jitter", [replace(e, position=Position(i * .00001, 0, e.observed_at, 10))
                        for i, e in enumerate(route)], ["recurring"],
         "Small position jitter does not create three separated locations."),
        ("stale_fixes", [replace(e, position=replace(e.position, measured_at=e.observed_at - 30))
                          for e in route], ["recurring"], "Old fixes cannot supply route evidence."),
        ("shared_ssid", [replace(route[0], address="02:00:00:00:00:02"), route[1]],
         ["observed", "observed"], "A shared network name does not join different radios."),
        ("replayed_same_event", [route[0]] * 100, ["observed"],
         "Repeated reading of one observation does not manufacture recurrence."),
    ]


def evaluate():
    rows = []
    for name, observations, expected, lesson in cases():
        report = summarize(observations, at=1200)
        actual = sorted(row["state"] for row in report["results"])
        rows.append({"case": name, "expected": sorted(expected), "actual": actual,
                     "policy_pass": actual == sorted(expected), "interpretation": lesson})
    return {"synthetic": True, "measures_rf_accuracy": False,
            "all_policy_checks_pass": all(row["policy_pass"] for row in rows), "cases": rows}


if __name__ == "__main__":
    result = evaluate()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_policy_checks_pass"] else 1)
