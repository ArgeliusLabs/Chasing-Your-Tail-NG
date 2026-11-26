"""Conservative offline joins to one observer's gpspipe -w JSON log.

No receiver control, interpolation, clock correction, or transmitter location.
gpsd error estimates are quality indicators, not guaranteed confidence bounds.
"""
from bisect import bisect_right
from dataclasses import dataclass, replace
from datetime import datetime
import json
import math

from .model import Position, number

MAX_LINES = 200000
MAX_LINE_CHARS = 65536


def utc_seconds(value):
    if not isinstance(value, str):
        raise ValueError("GPS time must be an ISO 8601 string with a timezone")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("GPS time needs an explicit timezone")
    result = parsed.timestamp()
    if result < 0:
        raise ValueError("GPS time cannot precede the Unix epoch")
    return result


def position_from_tpv(record, timestamp):
    """Missing/invalid fix fields become an outage barrier, never a guessed fix."""
    try:
        mode = record.get("mode")
        if type(mode) is not int or mode not in (2, 3):
            return None
        if "eph" in record:
            accuracy = number(record["eph"], "eph")
        else:
            ex = number(record["epx"], "epx")
            ey = number(record["epy"], "epy")
            if ex <= 0 or ey <= 0:
                return None
            accuracy = math.hypot(ex, ey)
        if accuracy <= 0:
            return None
        return Position(record["lat"], record["lon"], timestamp, accuracy, mode)
    except (KeyError, TypeError, ValueError):
        return None


@dataclass
class GPSTrack:
    times: list[float]
    positions: list[Position | None]
    stats: dict[str, int]

    def before(self, timestamp, *, max_age=5, max_accuracy=50):
        index = bisect_right(self.times, timestamp) - 1
        if index < 0:
            return None
        fix = self.positions[index]
        if fix is None or timestamp - fix.measured_at > max_age or fix.accuracy_m > max_accuracy:
            return None
        return fix


def read_gps(stream, *, device):
    """Require one explicitly selected gpsd device and nondecreasing fix times.

    Partial TPVs merge only within the same measurement timestamp. An untimed
    TPV invalidates the most recent epoch too: its precise outage time is unknown.
    This deliberately sacrifices some coverage instead of bridging a lost fix.
    """
    if not isinstance(device, str) or not device.strip():
        raise ValueError("GPS device must be nonempty")
    times, positions, epoch = [], [], {}
    stats = {"lines": 0, "selected_tpv": 0, "untimed_tpv": 0}
    while True:
        line = stream.readline(MAX_LINE_CHARS + 1)
        if not line:
            break
        stats["lines"] += 1
        if stats["lines"] > MAX_LINES or len(line) > MAX_LINE_CHARS:
            raise ValueError("GPS log exceeds line/count limit; split it into trips")
        if not line.strip():
            continue
        try:
            record = json.loads(line)
            if not isinstance(record, dict):
                raise ValueError("GPS log records must be objects")
            if record.get("class") != "TPV":
                continue
            if not isinstance(record.get("device"), str) or not record["device"]:
                raise ValueError("TPV record lacks a device; cannot establish GPS source")
            if record.get("device") != device:
                continue
            stats["selected_tpv"] += 1
            if "time" not in record:
                stats["untimed_tpv"] += 1
                epoch = {}
                if positions:
                    positions[-1] = None
                continue
            timestamp = utc_seconds(record["time"])
            if times and timestamp < times[-1]:
                raise ValueError("GPS time moved backwards; check clocks and split the log")
            if not times or timestamp != times[-1]:
                times.append(timestamp)
                positions.append(None)
                epoch = {}
            # A loss of fix clears even partial fields from this epoch.
            if record.get("mode") not in (2, 3):
                epoch = {}
                positions[-1] = None
                continue
            epoch.update(record)
            positions[-1] = position_from_tpv(epoch, timestamp)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"GPS line {stats['lines']}: {error}") from error
    if not stats["selected_tpv"]:
        raise ValueError("no TPV records match --gps-device")
    stats.update({"epochs": len(times), "complete_fix_epochs": sum(p is not None for p in positions)})
    return GPSTrack(times, positions, stats)


def geotag(observations, track, *, session, observer, max_age=5, max_accuracy=50, stats=None):
    for name, value in (("max_age", max_age), ("max_accuracy", max_accuracy)):
        if number(value, name) <= 0:
            raise ValueError(f"{name} must be positive")
    if not session.strip() or not observer.strip():
        raise ValueError("session and observer must be nonempty")
    stats = stats if stats is not None else {}
    stats.update({"observations": 0, "attached": 0, "preserved": 0, "unlocated": 0})
    for event in observations:
        if event.session != session or event.observer != observer:
            raise ValueError("observation session/observer does not match the GPS join scope")
        stats["observations"] += 1
        if event.position is not None:
            stats["preserved"] += 1
            yield event
            continue
        fix = track.before(event.observed_at, max_age=max_age, max_accuracy=max_accuracy)
        stats["attached" if fix is not None else "unlocated"] += 1
        yield replace(event, position=fix)
