"""Small data contract shared by future capture adapters and offline replay."""
from dataclasses import dataclass
import math
import re


def number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}", value):
        raise ValueError("address must be six colon-separated hexadecimal bytes")
    return value.upper()


@dataclass(frozen=True)
class Position:
    """The observer's measured position; never an estimated radio position."""
    latitude: float
    longitude: float
    measured_at: float
    accuracy_m: float
    fix_mode: int = 3

    def __post_init__(self):
        for field in ("latitude", "longitude", "measured_at", "accuracy_m"):
            number(getattr(self, field), field)
        if not -90 <= self.latitude <= 90 or not -180 <= self.longitude <= 180:
            raise ValueError("position outside latitude/longitude bounds")
        if self.accuracy_m < 0 or self.measured_at < 0:
            raise ValueError("accuracy and timestamp cannot be negative")
        if type(self.fix_mode) is not int or self.fix_mode not in (0, 1, 2, 3):
            raise ValueError("fix_mode must be an integer from 0 to 3")


@dataclass(frozen=True)
class Observation:
    session: str
    observer: str
    protocol: str
    address: str
    observed_at: float
    kind: str
    ssid: str | None = None
    rssi_dbm: float | None = None
    position: Position | None = None
    address_type: str = "unknown"

    def __post_init__(self):
        if not all(isinstance(s, str) and s.strip() for s in (self.session, self.observer)):
            raise ValueError("session and observer must be nonempty strings")
        if self.protocol not in ("wifi", "ble"):
            raise ValueError("protocol must be wifi or ble")
        kinds = {"wifi": {"probe", "beacon", "data_header", "device_summary"},
                 "ble": {"advertisement", "device_summary"}}
        if self.kind not in kinds[self.protocol]:
            raise ValueError("kind is incompatible with protocol")
        object.__setattr__(self, "address", address(self.address))
        if number(self.observed_at, "observed_at") < 0:
            raise ValueError("timestamp cannot be negative")
        if self.ssid is not None and not isinstance(self.ssid, str):
            raise ValueError("ssid must be a string or null")
        if self.ssid is not None and len(self.ssid.encode("utf-8")) > 32:
            raise ValueError("decoded UTF-8 SSID exceeds 32 bytes")
        if self.protocol != "wifi" and self.ssid is not None:
            raise ValueError("BLE observation cannot carry a Wi-Fi SSID")
        if self.rssi_dbm is not None:
            number(self.rssi_dbm, "rssi_dbm")
        if self.position is not None and not isinstance(self.position, Position):
            raise ValueError("position must be a Position or null")
        if self.protocol == "wifi":
            if int(self.address[:2], 16) & 1:
                raise ValueError("observed transmitter must have a unicast Wi-Fi address")
            kind = "locally_administered" if int(self.address[:2], 16) & 2 else "universally_administered"
            object.__setattr__(self, "address_type", kind)
        elif self.address_type not in {"unknown", "public", "static_random", "private_resolvable", "private_nonresolvable"}:
            raise ValueError("unsupported BLE address type")

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        position = values.get("position")
        if position is not None:
            values["position"] = Position(**position)
        return cls(**values)

    @property
    def key(self):
        return (self.session, self.observer, self.protocol, self.address)

    @property
    def event_key(self):
        # Re-polling an unchanged device summary must not create a new sighting.
        return (*self.key, self.observed_at, self.kind)


@dataclass(frozen=True)
class Rules:
    window_seconds: float = 1200
    bucket_seconds: float = 60
    min_buckets: int = 3
    min_span_seconds: float = 120
    min_locations: int = 3
    separation_m: float = 250
    max_fix_age_seconds: float = 5
    max_accuracy_m: float = 50

    def __post_init__(self):
        for name in ("window_seconds", "bucket_seconds", "min_span_seconds", "separation_m", "max_fix_age_seconds", "max_accuracy_m"):
            if number(getattr(self, name), name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("min_buckets", "min_locations"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 2:
                raise ValueError(f"{name} must be an integer of at least 2")
