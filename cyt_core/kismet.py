"""Read-only, incremental packet adapter for the Kismet v11 database contract.

Reference: kismet-2026-10-R1, kis_databaselogfile.{h,cc}. This is an independent
decoder; it does not import Kismet's aggregate device summaries or payloads.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from .model import Observation
from .store import encoded, readonly
from .wifi import SkipFrame, decode

MAX_PACKET_BYTES = 65535
COLUMNS = {"ts_sec", "ts_usec", "dlt", "packet", "signal", "error", "phyname"}
SELECT = "rowid, ts_sec, ts_usec, dlt, substr(packet, 1, 65535) AS packet, length(packet) AS packet_size, signal, error, phyname"


def digest(row):
    values = [value.hex() if isinstance(value, bytes) else value for value in tuple(row)]
    return hashlib.sha256(encoded(values).encode()).hexdigest()


def ingest(path, store, *, session, observer, batch_size=1000, retention_before=None):
    """One bounded transaction. Safe to repeat after interruption or on file copies.

    Checkpoints and observations commit together. A capture ID uses its version
    and first packet (timestamp, PHY, bytes); renaming/copying a capture does not
    create new observations. Different runs/observers remain separate.
    """
    if not isinstance(session, str) or not session.strip() or not isinstance(observer, str) or not observer.strip():
        raise ValueError("session and observer must be nonempty")
    if type(batch_size) is not int or not 1 <= batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")
    path = Path(path).resolve()
    with_source = readonly(path)
    try:
        with_source.execute("BEGIN")  # Short, consistent view, including a live WAL.
        try:
            version = with_source.execute("SELECT db_version FROM KISMET").fetchone()
            columns = {r[1] for r in with_source.execute("PRAGMA table_info(packets)")}
            if version is None or version[0] != 11 or not COLUMNS <= columns:
                raise ValueError("expected Kismet database v11 with packet logging enabled")
            first = with_source.execute(f"SELECT {SELECT} FROM packets ORDER BY rowid LIMIT 1").fetchone()
        except sqlite3.DatabaseError as error:
            raise ValueError("not a supported Kismet packet database (expected v11)") from error
        if first is None:
            return {"path": str(path), "state": "empty_capture", "rows_read": 0,
                    "inserted": 0, "skipped": {}, "more": False}
        capture_id = "kismet-v11:" + digest(first)
        identity = hashlib.sha256(encoded([session, observer, capture_id]).encode()).hexdigest()
        # Serialize writers before reading the checkpoint; concurrent collectors cannot rewind it.
        store.db.execute("BEGIN IMMEDIATE")
        try:
            previous = store.db.execute("SELECT * FROM sources WHERE identity=?", (identity,)).fetchone()
            last_row = previous["last_row"] if previous else 0
            if previous:
                anchor = with_source.execute(f"SELECT {SELECT} FROM packets WHERE rowid=?", (last_row,)).fetchone()
                if anchor is None or digest(anchor) != previous["last_digest"]:
                    raise ValueError("capture was truncated or rewritten in place; restore the original capture or use a new session")
            rows = with_source.execute(f"SELECT {SELECT} FROM packets WHERE rowid>? ORDER BY rowid LIMIT ?",
                                       (last_row, batch_size)).fetchall()
            counts, inserted, latest = Counter(), 0, previous["last_packet_at"] if previous else None
            for row in rows:
                try:
                    if row["error"] != 0:
                        raise SkipFrame("kismet_flagged_error")
                    if row["phyname"] != "IEEE802.11":
                        raise SkipFrame("unsupported_phy")
                    if row["packet_size"] is not None and row["packet_size"] > MAX_PACKET_BYTES:
                        raise SkipFrame("oversized_packet")
                    sec, usec = row["ts_sec"], row["ts_usec"]
                    if type(sec) is not int or sec < 0 or type(usec) is not int or not 0 <= usec < 1000000:
                        raise SkipFrame("invalid_timestamp")
                    timestamp = sec + usec / 1000000
                    fields = decode(row["packet"], row["dlt"])
                    signal = row["signal"]
                    # Kismet writes zero when no signal measurement exists.
                    signal = signal if isinstance(signal, (int, float)) and -200 <= signal < 0 else None
                    event = Observation(session, observer, "wifi", observed_at=timestamp,
                                        rssi_dbm=signal, source_id=capture_id,
                                        event_id=str(row["rowid"]), **fields)
                    inserted += store.insert(event)
                    latest = timestamp if latest is None else max(latest, timestamp)
                except SkipFrame as error:
                    counts[str(error)] += 1
            totals = Counter(json.loads(previous["skipped"])) if previous else Counter()
            totals.update(counts)
            last = rows[-1] if rows else None
            store.db.execute("""INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(identity) DO UPDATE SET path=excluded.path, last_row=excluded.last_row,
                last_digest=excluded.last_digest, rows_read=excluded.rows_read, inserted=excluded.inserted,
                skipped=excluded.skipped, checked_at=excluded.checked_at, last_packet_at=excluded.last_packet_at""",
                (identity, str(path), session, observer, last["rowid"] if last else last_row,
                 digest(last) if last else previous["last_digest"],
                 (previous["rows_read"] if previous else 0) + len(rows),
                 (previous["inserted"] if previous else 0) + inserted, encoded(totals), time.time(), latest))
            removed = store.trim(retention_before)
            store.db.commit()
        except BaseException:
            store.db.rollback()
            raise
        return {"path": str(path), "state": "read", "rows_read": len(rows), "inserted": inserted,
                "skipped": dict(counts), "removed": removed, "more": len(rows) == batch_size,
                "last_row": last["rowid"] if last else last_row}
    finally:
        with_source.close()
