# Experimental runtime: installation and operation

This guide describes the experimental `cyt_core` runtime merged in PR #38. Python 3.10+ is required. The core has no third-party runtime dependencies. The legacy scripts and `requirements.txt` are a separate application.

## Install or run from source

Running `python -m cyt_core` from the repository root requires no installation. To install a `cyt` command in an isolated environment on Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps .
.venv/bin/cyt --help
```

On Windows PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install --no-deps .
.venv/Scripts/cyt --help
```

The build uses setuptools; pip may download that build tool unless it is already available through a configured build environment. Runtime operation itself needs no internet service. `cyt` and `python -m cyt_core` accept the same arguments. No shell activation, global installation, root privileges, hardcoded username, or WiGLE credential is needed for CYT. Radio capture permissions belong to the separately configured Kismet installation.

## Collection and session boundaries

Supply an explicit destination, session, and observer:

```sh
cyt ingest '/path/to/captures/*.kismet' --db /path/to/cyt.sqlite3 --session trip-001 --observer pi-01 --follow
```

The destination directory must exist. Keep it on a local filesystem where SQLite locking works. Use a separate database from Kismet. CYT checks its database application ID/schema and rejects an existing unrelated database. It opens capture files using SQLite `mode=ro` and reads short snapshots, including committed WAL records. Copying only a live main `.kismet` file may omit uncheckpointed WAL data; prefer reading the local live file or a properly completed capture.

The quoted glob is rediscovered each pass, including newly rotated filenames. Every file receives a bounded batch per pass. Captures remain partitioned by the supplied session and physical observer. A restart of the same run should reuse both names. Starting a different session intentionally allows the input to be analyzed as a separate run. Passing yesterday's captures into today's session will retain yesterday's source timestamps, not create new current observations; narrow the glob when beginning a new trip.

Each capture identity derives from its v11 first packet record, and each event identifies a row within that capture. Renaming or making an unchanged copy preserves this identity. This is an engineering deduplication key, not a forensic authenticity claim. Replacing a file with a different first packet starts a new capture. If a previously processed checkpoint row disappears or changes while the first packet remains the same, ingestion fails visibly. Restore the capture or deliberately use a new session; do not edit an active capture in place.

Observations and the checkpoint commit in one transaction. An interrupted batch rolls back both. Concurrent collectors serialize checkpoint updates. A capture row is counted once per session/observer, even after its old observation has been pruned. Separate Kismet rows, radio retransmissions, and captures of the same transmission by multiple receivers can still contribute separate records. Temporal recurrence uses distinct time bins and a minimum span, not raw packet volume.

## Supported input contract

The schema reference is the tagged Kismet [v11 declaration](https://github.com/kismetwireless/kismet/blob/kismet-2026-10-R1/kis_databaselogfile.h) and [packet table/writer](https://github.com/kismetwireless/kismet/blob/kismet-2026-10-R1/kis_databaselogfile.cc). The adapter requires `KISMET.db_version = 11` and packet columns `ts_sec`, `ts_usec`, `dlt`, `packet`, `signal`, `error`, and `phyname`. Other versions fail with a diagnostic; there is no silent fallback to device summaries.

- Wi-Fi only: `phyname = IEEE802.11` with raw 802.11 link type 105 or radiotap link type 127.
- Accepted evidence: probe requests, beacons, and data-frame transmitter headers. Association, probe-response, control, and other PHY/frame types are currently skipped.
- Address 2 is the transmitted frame's advertised transmitter. It is not necessarily the original network-layer sender behind an access point.
- Kismet-flagged errors, bad FCS flags, malformed/truncated frames, invalid transmitter addresses, invalid timestamps, and unsupported frames receive separate skip counts.
- The radiotap decoder follows its documented [header/alignment rules](https://www.radiotap.org/) and [flags](https://www.radiotap.org/fields/Flags.html). It uses the header length and only reads fields needed to handle FCS. It does not verify a raw frame's CRC independently.
- Empty SSID bytes remain `ssid=""`, `ssid_hex=""`. Non-UTF-8 SSIDs remain exact hex with `ssid=null`; valid UTF-8 has both forms. No historical probed-name map is presented as a fresh probe.
- Kismet's zero signal sentinel becomes `null`. CYT stores selected metadata, not packet payloads. Original payloads remain in Kismet's own log under the operator's Kismet configuration.
- The adapter omits Kismet packet GPS coordinates because the record does not carry the fix time and accuracy required by CYT. It does not invent accuracy or turn an average device position into a route.

The software contract is covered by synthetic fixtures, not a claim that every adapter/driver emits compatible packets. `missing_packet_bytes`, many malformed frames, or zero accepted rows should prompt inspection of capture logging, link type, and Kismet configuration. Kismet databases whose packet content was stripped cannot reconstruct those observations.

## Reports and known addresses

```sh
cyt report --db cyt.sqlite3 --window-seconds 1200
cyt report --db cyt.sqlite3 --at 1200 --window-seconds 300
cyt known add --db cyt.sqlite3 --protocol wifi --address 02:00:00:00:00:01 --label 'My test radio'
cyt known list --db cyt.sqlite3
cyt known remove --db cyt.sqlite3 --protocol wifi --address 02:00:00:00:00:01
cyt status --db cyt.sqlite3
cyt export --db cyt.sqlite3 --since 1000 > observations.jsonl
```

`--at` is a UTC Unix timestamp in seconds; omitted means now. `--window-seconds` is in seconds, not minutes. The interval includes both endpoints and excludes future observations. The report includes effective rules. Defaults require three 60-second time bins and at least 120 seconds between the first and last observation to call an identifier recurring. This does not link addresses across changes.

Known lists live in the CYT database. Addresses are case-normalized, survive restart, and are reread for every report. They suppress output rather than remove evidence. The explicit `--ignore wifi,MAC` report/replay option provides a temporary exclusion. There is no automatic import or overwrite of legacy personal ignore files. SSID-only exclusion is intentionally absent because unrelated radios can share a network name.

Valid JSONL imports can include `Position` metadata or BLE observations; see the model and fixed replay fixture. Imports are transactional and reject invalid records with a line number. `source_id`/`event_id` must appear together; real adapters should use them to distinguish frames with the same timestamp. Without provenance fields, the original replay key remains session/observer/protocol/address/time/kind and conflicting records fail.

Route evidence requires a qualifying fix mode, timestamp age, accuracy, and separation beyond both fixes' uncertainties. There is no live GPS or BLE collector yet. Observer anchors are capped at at least 32 per identifier to limit pairwise comparisons; `observer_location_count_capped` reports when the count is a lower bound. Coordinates never establish transmitter movement.

## Storage and health

The default write cap is **100,000 retained observations**. `--max-events` accepts 1–1,000,000. Every committed Kismet batch prunes oldest event-time rows beyond the cap. Follow mode also prunes observations older than **604,800 seconds (seven days)** relative to the computer clock; override with `--retention-seconds`. A dense capture can reach the row cap much sooner. One-shot ingestion and JSONL import apply the row cap without a wall-clock age cutoff, so old captures can be replayed.

Explicit pruning uses `cyt prune --db cyt.sqlite3 --before UNIX_SECONDS`. The checkpoint history survives pruning to prevent reimport from repopulating expired events. SQLite reuses freed pages; it does not necessarily shrink the file. This is a bounded observation count, not an absolute disk quota: source checkpoints and known-list entries remain until the store is retired. Archive/rotate the CYT store between projects as needed. Backup a live store using SQLite-aware tooling, not by assuming the main file contains all WAL updates.

The collector reads at most 1,000 rows per file per pass by default; `--batch-size` allows 1–10,000. Individual frame reads are capped at 65,535 bytes. It waits two seconds between caught-up polls; `--poll-seconds` must be at least 0.1. Error retries wait rather than spin. Very broad globs still require visiting every matched file; use a capture directory for the current run. Report queries use a time index and reject more than one million selected rows. In-memory analysis scales with the selected window; the original replay command remains intended for bounded fixture files.

`status` and the browser distinguish `empty`, `stale` (no accepted observation for more than 60 seconds), `clock_ahead`, and `recent_observations`. These are freshness labels, not RF coverage measurements. A quiet environment and a failed receiver may both appear stale. Source diagnostics show their last check, cumulative rows/insertions, and skip reasons. Collector errors and waiting-for-file status appear in its process output; the dashboard has no process supervisor or radio-driver health API.

## Local browser

```sh
cyt serve --db cyt.sqlite3 --port 8765
```

Open `http://127.0.0.1:8765`. The dashboard refreshes every five seconds and offers windows from five minutes to 24 hours. It displays at most 200 identifiers, prioritizing recurring and recently seen identifiers; JSON reports contain all selected results. SSIDs and labels are rendered as text, without HTML interpolation. No external fonts, scripts, map tiles, or telemetry are loaded.

The HTTP server is read-only, binds to IPv4 loopback, rejects foreign Host/Origin values, and has no configuration/scan/delete endpoint. For a Pi, run an authenticated SSH tunnel from your viewing computer:

```sh
ssh -N -L 8765:127.0.0.1:8765 user@your-pi
```

Then use the same local URL on the viewing computer. This is a local diagnostic interface, not an internet-facing service. There is no untested systemd installer in this milestone. SIGTERM stops collector/server loops; Ctrl+C exits the current command. Kismet is managed separately.

## Validation and remaining release gates

All 53 tests and installed-command smoke checks passed on Windows/Linux with Python 3.10/3.13 in [the runtime CI run](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/actions/runs/41714526125). The suite covers synthetic packet parsing, source immutability, live WAL append, restart, capture copy/rotation, conflicting input, transactional failure, concurrent collectors, retention, exact windows, persisted exclusions, CLI follow behavior, local HTTP restrictions, and existing recurrence/GPS rules. A local isolated installation check confirmed bundled dashboard assets; a browser check confirmed rendering and window selection without console warnings/errors.

Before a replacement release: test real Kismet files and capture hardware, actual receiver fix provenance, Pi installation/service behavior, endurance/storage costs, Pager firmware integration and display, and BLE capture. See the [field plan](FIELD_VALIDATION_PLAN.md). The available code does not establish measured detection accuracy, reliable person identification, or a preconfigured hardware product ready to sell.
