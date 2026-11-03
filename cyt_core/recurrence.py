"""Explain recurrence of observed addresses without assigning threat probabilities."""
from collections import defaultdict
from dataclasses import asdict
import math

from .model import Rules, address, number


def distance_m(a, b):
    lat1, lat2 = math.radians(a.latitude), math.radians(b.latitude)
    dlat = lat2 - lat1
    dlon = math.radians(b.longitude - a.longitude)
    hav = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371000 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, hav))))


def summarize(observations, *, at, rules=None, ignored=()):
    """Analyze one bounded window; results are scoped to session and observer.

    `ignored` contains (protocol, address) pairs. Different MACs are never joined,
    even if they have the same SSID, manufacturer, timing, or signal strength.
    """
    number(at, "at")
    rules = rules or Rules()
    ignored = {(protocol, address(mac)) for protocol, mac in ignored}
    groups = defaultdict(list)
    seen = {}
    excluded = {"outside_window": 0, "ignored": 0, "duplicates": 0}
    for event in observations:
        if not at - rules.window_seconds <= event.observed_at <= at:
            excluded["outside_window"] += 1
            continue
        if (event.protocol, event.address) in ignored:
            excluded["ignored"] += 1
            continue
        if event.event_key in seen:
            if seen[event.event_key] != event:
                raise ValueError("conflicting observations with the same event key")
            excluded["duplicates"] += 1
            continue
        seen[event.event_key] = event
        groups[event.key].append(event)

    results = []
    for key, events in sorted(groups.items()):
        events.sort(key=lambda e: e.observed_at)
        buckets = {math.floor(e.observed_at / rules.bucket_seconds) for e in events}
        span = events[-1].observed_at - events[0].observed_at
        anchors = []
        valid_fixes = 0
        for event in events:
            pos = event.position
            if pos is None or pos.fix_mode < 2 or pos.accuracy_m > rules.max_accuracy_m:
                continue
            if abs(event.observed_at - pos.measured_at) > rules.max_fix_age_seconds:
                continue
            valid_fixes += 1
            # Require separation beyond the stated uncertainty on both fixes.
            if len(anchors) < max(32, rules.min_locations) and all(distance_m(pos, other) > rules.separation_m + pos.accuracy_m + other.accuracy_m
                   for other in anchors):
                anchors.append(pos)
        recurring = len(buckets) >= rules.min_buckets and span >= rules.min_span_seconds
        level = "observed"
        if recurring:
            level = "recurring_across_locations" if len(anchors) >= rules.min_locations else "recurring"
        results.append({
            "session": key[0], "observer": key[1], "protocol": key[2], "address": key[3],
            "address_types": sorted({e.address_type for e in events}),
            "state": level, "observations": len(events), "time_buckets": len(buckets),
            "first_observed_at": events[0].observed_at, "last_observed_at": events[-1].observed_at,
            "span_seconds": span, "distinct_observer_locations": len(anchors),
            "observer_location_count_capped": len(anchors) == max(32, rules.min_locations),
            "observations_with_usable_position": valid_fixes,
            "observation_kinds": sorted({e.kind for e in events}),
            "directed_ssids": sorted({e.ssid for e in events if e.kind == "probe" and e.ssid}),
            "directed_ssid_hex": sorted({e.ssid_hex for e in events if e.kind == "probe" and e.ssid_hex}),
            "wildcard_probes": sum(e.kind == "probe" and e.ssid == "" for e in events),
            "evidence": f"Same advertised address in {len(buckets)} time bins; {len(anchors)} separated observer locations.",
        })
    return {
        "schema_version": 1, "analysis_time": at, "window_seconds": rules.window_seconds,
        "rules": asdict(rules),
        "observed_identifiers": len(results), "excluded": excluded, "results": results,
        "interpretation": "Address recurrence is not proof of device identity, a person, or following. Capture coverage is not measured; missing observations do not mean an area is clear.",
    }
