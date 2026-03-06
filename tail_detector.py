"""
tail_detector.py — SentinelWatch Core Detection Engine
Surveillance detection system for macOS using Kismet as a backend.
🔒 SECURE MODE: Uses SecureKismetDB for SQL injection prevention.
"""

import glob
import json
import os
import sqlite3
import smtplib
import subprocess
from secure_database import SecureKismetDB
import csv
import threading
import time
import platform
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import Optional

# Try colorama, fall back to ANSI
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

# Try rich for pretty tables
try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    HAS_RICH = True
    console = Console()
except ImportError:
    HAS_RICH = False
    console = None

_RED    = "\033[91m"
_ORANGE = "\033[38;5;208m"
_GREEN  = "\033[92m"
_CYAN   = "\033[96m"
_YELLOW = "\033[93m"
_GRAY   = "\033[90m"
_BOLD   = "\033[1m"
_RESET  = "\033[0m"

# ──────────────────────────────────────────────
#  OUI vendor lookup
# ──────────────────────────────────────────────
KNOWN_OUI = {
    "00:17:f2": "Apple",    "00:1c:b3": "Apple",    "00:23:12": "Apple",
    "00:26:bb": "Apple",    "04:26:65": "Apple",     "10:dd:b1": "Apple",
    "18:af:61": "Apple",    "28:cf:e9": "Apple",     "34:c0:59": "Apple",
    "40:d3:2d": "Apple",    "58:55:ca": "Apple",     "60:03:08": "Apple",
    "70:56:81": "Apple",    "78:4f:43": "Apple",     "90:60:f1": "Apple",
    "a4:d1:8c": "Apple",    "b0:65:bd": "Apple",     "d0:03:4b": "Apple",
    "e0:f5:c6": "Apple",    "f0:18:98": "Apple",     "f4:f1:5a": "Apple",
    "00:17:c8": "Samsung",  "08:fc:88": "Samsung",   "18:89:5b": "Samsung",
    "38:01:46": "Samsung",  "44:a7:cf": "Samsung",   "60:6b:bd": "Samsung",
    "90:18:7c": "Samsung",  "b4:3a:28": "Samsung",   "d0:22:be": "Samsung",
    "00:0c:e7": "Google",   "3c:5a:b4": "Google",    "54:60:09": "Google",
    "f4:f5:d8": "Google",
    "00:21:6a": "Amazon",   "38:f7:3d": "Amazon",    "40:b4:cd": "Amazon",
    "74:75:48": "Amazon",   "a0:02:dc": "Amazon",
    "00:0d:93": "Netgear",  "30:46:9a": "Netgear",   "b0:7f:b9": "Netgear",
    "00:1d:7e": "Cisco",    "2c:54:2d": "Cisco",     "58:ac:78": "Cisco",
    "00:18:60": "Ring",     "28:6d:97": "Ring",      "30:81:71": "Ring",
    "2c:aa:8e": "Ring",     "00:04:4b": "Nvidia",
}

def lookup_manufacturer(mac: str) -> str:
    return KNOWN_OUI.get(mac[:8].lower(), "Unknown")


# ──────────────────────────────────────────────
#  Global alert queue for SSE
# ──────────────────────────────────────────────
_alert_queue: list = []
_alert_lock = threading.Lock()

def _push_alert(level: str, message: str):
    with _alert_lock:
        _alert_queue.append({
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        if len(_alert_queue) > 200:
            _alert_queue.pop(0)

def get_recent_alerts(limit: int = 50) -> list:
    with _alert_lock:
        return list(_alert_queue[-limit:])


# ──────────────────────────────────────────────
#  DeviceProfile
# ──────────────────────────────────────────────
@dataclass
class DeviceProfile:
    mac: str
    label: str = ""
    group: str = "unknown"
    manufacturer: str = ""
    ssids: list = field(default_factory=list)
    first_seen: str = ""
    last_seen: str = ""
    total_encounters: int = 0
    home_encounters: int = 0
    roam_encounters: int = 0
    encounter_score: float = 0.0
    signal_history: list = field(default_factory=list)
    signal_trend: str = "unknown"
    modes_seen_in: list = field(default_factory=list)
    notes: str = ""
    is_watchlisted: bool = False
    cross_mode_detected: bool = False
    # Linger tracking (doorbell / home)
    first_seen_this_session: str = ""

    def display_name(self) -> str:
        return self.label if self.label else self.mac

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "DeviceProfile":
        valid = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in d.items() if k in valid})


# ──────────────────────────────────────────────
#  TailDetector
# ──────────────────────────────────────────────
class TailDetector:
    def __init__(self, config_path: str = "config.json"):
        with open(config_path, "r") as f:
            self.config = json.load(f)

        self.config_path = config_path
        self.whitelist_path = self.config["paths"]["whitelist"]
        self.alerts_log = self.config["paths"]["alerts_log"]
        self.kismet_glob = self.config["paths"]["kismet_logs"]
        self.thresholds = self.config["thresholds"]
        self.alert_cfg = self.config["alerts"]
        self.timing = self.config["timing"]

        # Linger tracking: mac → datetime first seen this session
        self._linger_first_seen: dict[str, datetime] = {}
        self._linger_alerted: set = set()

        os.makedirs(os.path.dirname(self.whitelist_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.alerts_log), exist_ok=True)
        os.makedirs(self.config["paths"]["log_dir"], exist_ok=True)

        self.devices: dict[str, DeviceProfile] = {}
        self.current_mode: str = "IDLE"
        self.present_macs: set = set()

        self._load_whitelist()

        # Import notifications lazily (so it works even if resend/twilio not installed)
        try:
            import notifications as _notif
            self._notif = _notif
        except ImportError:
            self._notif = None

    # ─── Whitelist ────────────────────────────
    def _load_whitelist(self):
        if os.path.exists(self.whitelist_path):
            try:
                with open(self.whitelist_path, "r") as f:
                    data = json.load(f)
                for mac, d in data.items():
                    self.devices[mac] = DeviceProfile.from_dict(d)
            except Exception as e:
                self.fire_alert("WARNING", f"Could not load whitelist: {e}")

    def _save_whitelist(self):
        try:
            os.makedirs(os.path.dirname(self.whitelist_path), exist_ok=True)
            with open(self.whitelist_path, "w") as f:
                json.dump({mac: p.to_dict() for mac, p in self.devices.items()}, f, indent=2)
        except Exception as e:
            self.fire_alert("WARNING", f"Could not save whitelist: {e}")

    # ─── Kismet DB ────────────────────────────
    def _get_kismet_files(self, hours: Optional[int] = None) -> list[str]:
        # Try configured path first
        pattern = self.config["paths"]["kismet_logs"]
        if pattern.startswith("~"):
            pattern = os.path.expanduser(pattern)
            
        files = glob.glob(pattern)
        
        # Fallback 1: Home directory
        if not files:
            files = glob.glob(os.path.join(str(Path.home()), "*.kismet"))
            
        # Fallback 2: Linux standard path
        if not files and platform.system() == "Linux":
            files = glob.glob("/var/lib/kismet/*.kismet")
            
        if hours is not None:
            cutoff = datetime.now() - timedelta(hours=hours)
            files = [f for f in files
                     if datetime.fromtimestamp(os.path.getmtime(f)) >= cutoff]
        return sorted(files)

    def _parse_kismet_db(self, db_path: str) -> list[dict]:
        """🔒 Secure: uses parameterized SecureKismetDB — no raw SQL concatenation."""
        devices = []
        try:
            with SecureKismetDB(db_path) as db:
                if not db.validate_connection():
                    self.fire_alert("WARNING", f"DB validation failed: {db_path}")
                    return []
                rows = db.execute_safe_query(
                    "SELECT devmac, type, device, first_time, last_time, "
                    "avg_lat, avg_lon, strongest_signal FROM devices"
                )
                for row in rows:
                    try:
                        blob = json.loads(row["device"]) if row["device"] else {}
                        ssids = self._extract_ssids(blob)
                        devices.append({
                            "mac": row["devmac"],
                            "type": row["type"],
                            "first_time": row["first_time"],
                            "last_time": row["last_time"],
                            "avg_lat": row["avg_lat"],
                            "avg_lon": row["avg_lon"],
                            "signal": row["strongest_signal"],
                            "ssids": ssids,
                            "manufacturer": blob.get("kismet.device.base.manuf", "")
                                           or lookup_manufacturer(row["devmac"]),
                        })
                    except Exception:
                        pass
        except Exception as e:
            self.fire_alert("WARNING", f"DB parse error {db_path}: {e}")
        return devices

    def _extract_ssids(self, blob: dict) -> list[str]:
        ssids = []
        try:
            for key in ["dot11.device.probed_ssid_map", "dot11.device.advertised_ssid_map"]:
                mp = blob.get("dot11.device", {}).get(key, {})
                if isinstance(mp, dict):
                    for v in mp.values():
                        s = v.get("dot11.probedssid.ssid") or v.get("dot11.advertisedssid.ssid", "")
                        if s and s not in ssids:
                            ssids.append(s)
        except Exception:
            pass
        return ssids

    def _update_profile(self, raw: dict, mode: str) -> DeviceProfile:
        mac = raw["mac"]
        manufacturer = raw.get("manufacturer") or lookup_manufacturer(mac)
        now_dt = datetime.now()
        last_dt = datetime.fromtimestamp(raw["last_time"]) if raw.get("last_time") else now_dt
        first_dt = datetime.fromtimestamp(raw["first_time"]) if raw.get("first_time") else now_dt

        if mac not in self.devices:
            self.devices[mac] = DeviceProfile(
                mac=mac,
                manufacturer=manufacturer,
                ssids=raw.get("ssids", []),
                first_seen=first_dt.isoformat(),
                last_seen=last_dt.isoformat(),
                total_encounters=0,
            )
        p = self.devices[mac]
        p.total_encounters += 1
        p.last_seen = last_dt.isoformat()
        if not p.manufacturer or p.manufacturer == "Unknown":
            p.manufacturer = manufacturer
        for s in raw.get("ssids", []):
            if s and s not in p.ssids:
                p.ssids.append(s)
        if raw.get("signal") is not None:
            p.signal_history.append(raw["signal"])
            if len(p.signal_history) > 20:
                p.signal_history = p.signal_history[-20:]
        if mode and mode not in p.modes_seen_in:
            p.modes_seen_in.append(mode)
        return p

    # ─── Scoring ──────────────────────────────
    def _recency_score(self, last_seen_iso: str) -> float:
        try:
            days = max(0, (datetime.now() - datetime.fromisoformat(last_seen_iso)).total_seconds() / 86400)
            return 1.0 / (1 + days)
        except Exception:
            return 0.1

    def _compute_score(self, p: DeviceProfile) -> float:
        return p.total_encounters * self._recency_score(p.last_seen)

    # ─── Signal trend ─────────────────────────
    def calculate_signal_trend(self, mac: str) -> str:
        if mac not in self.devices:
            return "unknown"
        hist = self.devices[mac].signal_history[-5:]
        if len(hist) < 2:
            return "unknown"
        delta = hist[-1] - hist[0]
        if delta > 5:
            return "approaching"
        elif delta < -5:
            return "receding"
        return "stable"

    # ─── Linger check ─────────────────────────
    def _check_linger(self, mac: str, ssids: list, signal: Optional[int]):
        """Track how long an unknown device has been nearby. Fire alert if > threshold."""
        linger_min = self.timing.get("unknown_ssid_linger_minutes", 5)
        now = datetime.now()

        if mac not in self.devices or not self.devices[mac].label:
            if mac not in self._linger_first_seen:
                self._linger_first_seen[mac] = now
            else:
                elapsed = (now - self._linger_first_seen[mac]).total_seconds() / 60
                if elapsed >= linger_min and mac not in self._linger_alerted:
                    self._linger_alerted.add(mac)
                    ssid_str = ssids[0] if ssids else "(hidden)"
                    self.fire_alert(
                        "WARNING",
                        f"LINGERING: {mac} ({ssid_str}) {elapsed:.1f}min"
                    )
                    if self._notif:
                        self._notif.notify_unknown_ssid_linger(
                            ssid_str, mac, elapsed, signal, self.config)
        else:
            self._linger_first_seen.pop(mac, None)
            self._linger_alerted.discard(mac)

    # ─── Alerts ───────────────────────────────
    def fire_alert(self, level: str, message: str):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _push_alert(level, message)

        if self.alert_cfg.get("log_alerts", True):
            try:
                with open(self.alerts_log, "a") as f:
                    f.write(f"[{ts}] [{level}] {message}\n")
            except Exception:
                pass

        if self.alert_cfg.get("console_alerts", True):
            if level == "CRITICAL":
                w = max(len(message) + 4, 36)
                b = "─" * w
                print(f"\n{_RED}{_BOLD}┌{b}┐")
                print(f"│  ⚠  CRITICAL ALERT{' '*(w-19)}│")
                print(f"│  {message[:w-4]:<{w-4}}│")
                print(f"└{b}┘{_RESET}\n")
            elif level == "WARNING":
                print(f"{_ORANGE}[{ts}] ⚡ WARNING: {message}{_RESET}")
            else:
                print(f"{_CYAN}[{ts}] ℹ  INFO: {message}{_RESET}")

    # ─── Cross-mode detection ─────────────────
    def _check_cross_mode(self, p: DeviceProfile, current_mode: str):
        other = "ROAM" if current_mode == "HOME" else "HOME"
        if other in p.modes_seen_in and not p.cross_mode_detected:
            p.cross_mode_detected = True
            msg = f"⚠ CROSS-MODE: {p.display_name()} seen in ROAMING & STATIONARY"
            self.fire_alert("CRITICAL", msg)
            if self._notif:
                self._notif.dispatch_alert("CRITICAL", msg, self.config)

    # ═══════════════════════════════════════════
    #  CONSOLIDATED MODES (Phase 8)
    # ═══════════════════════════════════════════

    def run_stationary_mode(self, doorbell_alerts: bool = False):
        """
        Consolidated STATIONARY mode. Performs both batch scanning (Home)
        and optional real-time arrival/departure tracking (Doorbell).
        """
        self.current_mode = "STATIONARY"
        alert_msg = "STATIONARY mode started" + (" (with Doorbell Alerts)" if doorbell_alerts else "")
        self.fire_alert("INFO", alert_msg)
        
        interval = self.timing.get("doorbell_scan_interval", 10)
        unknown_streak: dict[str, int] = {}
        prev_present: set = set()

        while not _push_alert.__globals__.get('_bg_stop_event').is_set():
            files = self._get_kismet_files(hours=1)
            current_macs: set = set()
            
            for db_path in files:
                for raw in self._parse_kismet_db(db_path):
                    # Basic update
                    p = self._update_profile(raw, "STATIONARY")
                    p.home_encounters += 1
                    p.encounter_score = self._compute_score(p)
                    p.signal_trend = self.calculate_signal_trend(p.mac)
                    
                    # Stationary specific logic
                    if raw.get("last_time"):
                        age = datetime.now() - datetime.fromtimestamp(raw["last_time"])
                        if age <= timedelta(seconds=interval * 3):
                            current_macs.add(p.mac)

                    # Doorbell functionality (if enabled)
                    if doorbell_alerts and p.mac not in prev_present:
                        self._handle_arrival(p, raw, unknown_streak)

                    # Linger check (always active in stationary)
                    if not p.label:
                        self._check_linger(p.mac, p.ssids, raw.get("signal"))
                    
                    self._check_cross_mode(p, "STATIONARY")

            # Departure logic (if enabled)
            if doorbell_alerts:
                for mac in prev_present - current_macs:
                    self._handle_departure(mac, unknown_streak)

            self.present_macs = current_macs
            prev_present = set(current_macs)
            self._save_whitelist()
            time.sleep(interval)

    def _handle_arrival(self, p: DeviceProfile, raw: dict, unknown_streak: dict):
        name = p.display_name()
        if p.label:
            self.fire_alert("INFO", f"ARRIVED: {name}")
            if self._notif and self.alert_cfg.get("known_device_arrival_notify"):
                self._notif.notify_known_arrival(name, p.mac, raw.get("signal"), self.config)
        else:
            unknown_streak[p.mac] = unknown_streak.get(p.mac, 0) + 1
            if p.is_watchlisted:
                msg = f"⚠ WATCHLIST: {name} ({p.manufacturer})"
                self.fire_alert("CRITICAL", msg)
                if self._notif:
                    self._notif.notify_watchlist_hit(name, p.mac, raw.get("signal"), p.notes, self.config)
            else:
                lvl = "WARNING" if unknown_streak[p.mac] >= 3 else "INFO"
                self.fire_alert(lvl, f"NEW: {name} ({p.manufacturer})")

    def _handle_departure(self, mac: str, unknown_streak: dict):
        p = self.devices.get(mac)
        name = p.display_name() if p else mac
        self.fire_alert("INFO", f"LEFT: {name}")
        unknown_streak.pop(mac, None)
        self._linger_first_seen.pop(mac, None)
        self._linger_alerted.discard(mac)

    # ═══════════════════════════════════════════
    #  MODE 2: ROAMING
    # ═══════════════════════════════════════════
    def run_roaming_mode(self, hours: int = 24, continuous: bool = True):
        self.current_mode = "ROAMING"
        self.fire_alert("INFO", f"ROAMING mode started — scanning last {hours}h")
        interval = self.timing.get("roam_scan_interval", 15)

        def _scan():
            files = self._get_kismet_files(hours=hours)
            if not files:
                self.fire_alert("WARNING", "No recent .kismet files found.")
                return
            poi_macs = set()
            for db_path in files:
                for raw in self._parse_kismet_db(db_path):
                    mac = raw["mac"]
                    p = self._update_profile(raw, "ROAMING")
                    p.encounter_score = self._compute_score(p)
                    p.signal_trend = self.calculate_signal_trend(mac)

                    if "STATIONARY" not in p.modes_seen_in:
                        p.roam_encounters += 1
                        poi_macs.add(mac)

                    if p.is_watchlisted:
                        msg = f"WATCHLISTED device detected: {p.display_name()} ({mac})"
                        self.fire_alert("CRITICAL", msg)
                        if self._notif:
                            self._notif.notify_watchlist_hit(p.label, mac, raw.get("signal"), p.notes, self.config)

                    thresh = self.thresholds.get("signal_approaching_threshold", -65)
                    if p.signal_trend == "approaching" and (raw.get("signal") or -100) > thresh:
                        self.fire_alert("WARNING", f"Device approaching: {p.display_name()} ({mac}) {raw.get('signal')} dBm ↑")

                    if "STATIONARY" in p.modes_seen_in:
                        self._check_cross_mode(p, "ROAMING")

            pois = sorted([self.devices[m] for m in poi_macs if m in self.devices], key=lambda x: x.encounter_score, reverse=True)
            self._print_roam_table(pois[:20])
            self._save_whitelist()

        if continuous:
            while not _push_alert.__globals__.get('_bg_stop_event').is_set():
                _scan()
                time.sleep(interval)
        else:
            _scan()

    def _print_roam_table(self, pois):
        trend_map = {"approaching": "↑ APPROACH", "receding": "↓ RECEDING", "stable": "→ STABLE"}
        if HAS_RICH:
            t = Table(title="🚗  SentinelWatch — Persons of Interest (ROAM)", box=box.ROUNDED,
                      header_style="bold red", border_style="red")
            t.add_column("Rank", width=5); t.add_column("MAC"); t.add_column("Mfr")
            t.add_column("R.Enc", justify="right"); t.add_column("Score", justify="right")
            t.add_column("Signal", justify="right"); t.add_column("Trend"); t.add_column("SSIDs")
            for i, p in enumerate(pois, 1):
                sig = str(p.signal_history[-1]) if p.signal_history else "?"
                trend = trend_map.get(p.signal_trend, "?")
                col = "red" if p.signal_trend == "approaching" else ("green" if p.signal_trend == "receding" else "yellow")
                t.add_row(f"#{i}", p.mac, p.manufacturer, str(p.roam_encounters),
                          f"{p.encounter_score:.2f}", sig, f"[{col}]{trend}[/{col}]",
                          ", ".join(p.ssids[:2]))
            console.print(t)

    # ═══════════════════════════════════════════
    #  MODE 3: WATCHLIST
    # ═══════════════════════════════════════════
    def run_watchlist_mode(self):
        self.current_mode = "WATCHLIST"
        watchlist = self.get_watchlist()
        if not watchlist:
            self.fire_alert("INFO", "Watchlist empty.")
            return
        self.fire_alert("INFO", f"WATCHLIST mode — monitoring {len(watchlist)} devices")
        w_macs = {p.mac for p in watchlist}

        while not _push_alert.__globals__.get('_bg_stop_event').is_set():
            for db_path in self._get_kismet_files(hours=1):
                for raw in self._parse_kismet_db(db_path):
                    if raw["mac"] in w_macs:
                        p = self.devices[raw["mac"]]
                        msg = f"WATCHLISTED: {p.display_name()} ({p.mac}) Signal:{raw.get('signal','?')} dBm"
                        self.fire_alert("CRITICAL", msg)
                        if self._notif:
                            self._notif.notify_watchlist_hit(p.label, p.mac, raw.get("signal"), p.notes, self.config)
            time.sleep(30)


    # ═══════════════════════════════════════════
    #  Utility
    # ═══════════════════════════════════════════
    def label_device(self, mac: str, label: str, group: str = "unknown", notes: str = ""):
        if mac not in self.devices:
            self.devices[mac] = DeviceProfile(mac=mac)
        p = self.devices[mac]
        p.label = label; p.group = group
        if notes: p.notes = notes
        self._save_whitelist()
        self.fire_alert("INFO", f"Labeled: {mac} → '{label}' ({group})")

    def add_to_watchlist(self, mac: str, reason: str = ""):
        if mac not in self.devices:
            self.devices[mac] = DeviceProfile(mac=mac)
        p = self.devices[mac]
        p.is_watchlisted = True; p.group = "watchlist"
        if reason: p.notes = f"WATCHLISTED: {reason}"
        self._save_whitelist()
        self.fire_alert("WARNING", f"Added to watchlist: {mac} — {reason}")

    def remove_from_watchlist(self, mac: str):
        if mac in self.devices:
            self.devices[mac].is_watchlisted = False
            if self.devices[mac].group == "watchlist":
                self.devices[mac].group = "unknown"
            self._save_whitelist()
            self.fire_alert("INFO", f"Removed from watchlist: {mac}")

    def get_top_visitors(self, limit: int = 10):
        stat = [p for p in self.devices.values()
                if "STATIONARY" in p.modes_seen_in or p.home_encounters > 0]
        return sorted(stat, key=lambda p: p.encounter_score, reverse=True)[:limit]

    def get_persons_of_interest(self, limit: int = 10):
        pois = [p for p in self.devices.values()
                if "STATIONARY" not in p.modes_seen_in and p.roam_encounters > 0]
        return sorted(pois, key=lambda p: p.encounter_score, reverse=True)[:limit]

    def get_watchlist(self):
        return [p for p in self.devices.values()
                if p.is_watchlisted or p.group == "watchlist"]

    def export_to_csv(self, filename: str):
        fieldnames = list(DeviceProfile.__dataclass_fields__.keys())
        with open(filename, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for p in self.devices.values():
                d = p.to_dict()
                for key in ("ssids", "signal_history", "modes_seen_in"):
                    d[key] = "|".join(map(str, d.get(key, [])))
                w.writerow(d)
        self.fire_alert("INFO", f"Exported {len(self.devices)} devices → {filename}")

    def export_to_json(self, filename: str):
        with open(filename, "w") as f:
            json.dump({mac: p.to_dict() for mac, p in self.devices.items()}, f, indent=2)
        self.fire_alert("INFO", f"Exported {len(self.devices)} devices → {filename}")

    def get_all_devices_list(self) -> list[dict]:
        result = []
        for p in sorted(self.devices.values(), key=lambda x: x.encounter_score, reverse=True):
            d = p.to_dict()
            d["signal_latest"] = p.signal_history[-1] if p.signal_history else None
            d["display_name"] = p.display_name()
            result.append(d)
        return result

    def _get_mac_idle_time(self) -> float:
        """Use ioreg to get macOS system idle time in seconds."""
        try:
            # No shell=True — pipe manually between two subprocesses
            ioreg = subprocess.Popen(
                ["ioreg", "-c", "IOHIDSystem"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            awk = subprocess.Popen(
                ["awk", "/HIDIdleTime/ {print $NF/1000000000; exit}"],
                stdin=ioreg.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
            )
            ioreg.stdout.close()
            out, _ = awk.communicate(timeout=5)
            result = out.decode().strip()
            return float(result) if result else 0.0
        except Exception:
            return 0.0

    def run_screensaver_mode(self, idle_threshold: int = 60):
        """
        Monitors system idle time. If idle > threshold, activate STATIONARY logic.
        If user returns, stop scanning.
        """
        self.current_mode = "SCREENSAVER"
        self.fire_alert("INFO", f"SCREENSAVER mode active (threshold: {idle_threshold}s)")
        
        is_scanning = False
        
        while not _push_alert.__globals__.get('_bg_stop_event').is_set():
            idle = self._get_mac_idle_time()
            
            if idle >= idle_threshold:
                if not is_scanning:
                    self.fire_alert("WARNING", "Idle detected: Starting background Sentinel scan")
                    is_scanning = True
                
                # Perform a single scan iteration (Stationary logic)
                files = self._get_kismet_files(hours=1)
                for db_path in files:
                    for raw in self._parse_kismet_db(db_path):
                        self._update_profile(raw, "STATIONARY")
                
                self.fire_alert("INFO", f"Screensaver scan complete. System still idle ({int(idle)}s)")
            else:
                if is_scanning:
                    self.fire_alert("INFO", "User returned: Sentinel scan paused")
                    is_scanning = False
            
            time.sleep(10)


# ── CLI ───────────────────────────────────────
if __name__ == "__main__":
    import sys
    mode = (sys.argv[1] if len(sys.argv) > 1 else "home").upper()
    td = TailDetector()
    if mode == "HOME":      td.run_home_mode()
    elif mode == "ROAM":    td.run_roam_mode()
    elif mode == "DOORBELL":td.run_doorbell_mode()
    elif mode == "WATCHLIST":td.run_watchlist_mode()
    else: print(f"Unknown mode: {mode}. Use: home|roam|doorbell|watchlist")
