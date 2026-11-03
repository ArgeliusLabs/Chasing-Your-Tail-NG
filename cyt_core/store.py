"""CYT-owned SQLite storage; source databases are never opened for writing."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from .model import Observation, address, number
from .recurrence import summarize

APPLICATION_ID = 0x43595432
SCHEMA_VERSION = 1


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True, timeout=2)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    return connection


class Store:
    def __init__(self, path, *, max_events=100000):
        if type(max_events) is not int or not 1 <= max_events <= 1000000:
            raise ValueError("max_events must be between 1 and 1000000")
        self.max_events = max_events
        self.db = sqlite3.connect(path, timeout=5)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute("BEGIN IMMEDIATE")
            identity = self.db.execute("PRAGMA application_id").fetchone()[0]
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if identity == 0 and version == 0 and not tables:
                schema = f"""
                        PRAGMA application_id={APPLICATION_ID};
                        PRAGMA user_version={SCHEMA_VERSION};
                        CREATE TABLE observations (
                            identity TEXT PRIMARY KEY, observed_at REAL NOT NULL,
                            protocol TEXT NOT NULL, address TEXT NOT NULL, body TEXT NOT NULL);
                        CREATE INDEX observations_time ON observations(observed_at);
                        CREATE TABLE sources (
                            identity TEXT PRIMARY KEY, path TEXT NOT NULL, session TEXT NOT NULL,
                            observer TEXT NOT NULL, last_row INTEGER NOT NULL,
                            last_digest TEXT NOT NULL, rows_read INTEGER NOT NULL,
                            inserted INTEGER NOT NULL, skipped TEXT NOT NULL,
                            checked_at REAL NOT NULL, last_packet_at REAL);
                        CREATE TABLE known (
                            protocol TEXT NOT NULL, address TEXT NOT NULL, label TEXT NOT NULL,
                            PRIMARY KEY(protocol, address));
                    """
                for statement in schema.split(";"):
                    if statement.strip():
                        self.db.execute(statement)
            elif identity != APPLICATION_ID or version != SCHEMA_VERSION:
                raise ValueError("not a supported CYT store; choose a new CYT database path")
            self.db.commit()
            self.db.execute("PRAGMA journal_mode=WAL")
        except Exception:
            self.db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def insert(self, event):
        identity = hashlib.sha256(encoded(event.event_key).encode()).hexdigest()
        body = encoded(asdict(event))
        previous = self.db.execute("SELECT body FROM observations WHERE identity=?", (identity,)).fetchone()
        if previous:
            if previous[0] != body:
                raise ValueError("conflicting observations with the same source event identity")
            return 0
        self.db.execute("INSERT INTO observations VALUES (?, ?, ?, ?, ?)",
                        (identity, event.observed_at, event.protocol, event.address, body))
        return 1

    def trim(self, before=None):
        """Call inside the same transaction as inserts/checkpoint advancement."""
        removed = 0
        if before is not None:
            number(before, "retention cutoff")
            removed += self.db.execute("DELETE FROM observations WHERE observed_at < ?", (before,)).rowcount
        excess = self.db.execute("SELECT MAX(COUNT(*) - ?, 0) FROM observations", (self.max_events,)).fetchone()[0]
        if excess:
            removed += self.db.execute("""DELETE FROM observations WHERE identity IN
                (SELECT identity FROM observations ORDER BY observed_at, identity LIMIT ?)""", (excess,)).rowcount
        return removed

    def report(self, *, at, rules, ignored=()):
        number(at, "at")
        known = [(r[0], r[1]) for r in self.db.execute("SELECT protocol, address FROM known")]
        rows = self.db.execute("""SELECT body FROM observations WHERE observed_at BETWEEN ? AND ?
            ORDER BY observed_at, identity LIMIT 1000001""", (at - rules.window_seconds, at)).fetchall()
        if len(rows) > 1000000:
            raise ValueError("report exceeds one million observations; reduce the window or prune the store")
        result = summarize((Observation.from_dict(json.loads(r[0])) for r in rows),
                           at=at, rules=rules, ignored=[*known, *ignored])
        result["storage"] = self.status(at=at)
        return result

    def status(self, *, at=None):
        at = time.time() if at is None else number(at, "at")
        row = self.db.execute("SELECT COUNT(*), MIN(observed_at), MAX(observed_at) FROM observations").fetchone()
        sources = []
        for entry in self.db.execute("SELECT * FROM sources ORDER BY path"):
            source = dict(entry)
            source["skipped"] = json.loads(source["skipped"])
            source["seconds_since_check"] = at - source["checked_at"]
            sources.append(source)
        age = None if row[2] is None else at - row[2]
        state = "empty" if age is None else "clock_ahead" if age < -5 else "stale" if age > 60 else "recent_observations"
        return {"schema_version": SCHEMA_VERSION, "observations": row[0], "oldest_observed_at": row[1],
                "newest_observed_at": row[2], "seconds_since_observation": age,
                "state": state, "max_events_on_write": self.max_events, "sources": sources,
                "coverage": "unknown", "gps": "not supplied by Kismet packet adapter"}

    def known(self, action, protocol=None, mac=None, label=""):
        if action == "list":
            return [dict(r) for r in self.db.execute("SELECT * FROM known ORDER BY protocol, address")]
        if protocol not in ("wifi", "ble"):
            raise ValueError("known identifiers require wifi or ble")
        mac = address(mac)
        with self.db:
            if action == "add":
                self.db.execute("INSERT INTO known VALUES (?, ?, ?) ON CONFLICT(protocol, address) DO UPDATE SET label=excluded.label",
                                (protocol, mac, label))
            elif action == "remove":
                self.db.execute("DELETE FROM known WHERE protocol=? AND address=?", (protocol, mac))
            else:
                raise ValueError("unknown known-list action")
        return self.known("list")
