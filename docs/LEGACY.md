# Legacy migration policy

Decision date: November 26, 2026.

The maintained development path is `cyt_core`. The older root scripts remain readable and runnable for migration and audit, but are not the supported route to the next CYT release. Their presence does not certify their detection logic, GPS correlation, security, or platform compatibility.

## What is being retired

The rewrite retires remembered-SSID history as its primary detector, WiGLE-derived claims about a person's origin, opaque surveillance scores, whole-log text parsing, and separate Tkinter/analysis pipelines. It will not acquire these behaviors merely to preserve an old interface. WiGLE lookup is absent from the core; no credential migration is needed for the new setup.

`chasing_your_tail.py`, `cyt_gui.py`, `probe_analyzer.py`, `surveillance_*`, `gps_tracker.py`, the `secure_*` helpers, root shell launchers, root `config.json`, and `requirements.txt` belong to the historical application. The current core uses explicit command arguments and its own store. A new browser UI does not automatically repair old GUI bugs.

The small filename correction from community [PR #10](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/pull/10) is incorporated: legacy configuration names the JSON ignore files. The capture glob is now relative instead of pointing at one developer's home directory. This does not repair legacy SSID generation or certify its parser on every SQLite build. The original filename defect remains an explicitly historical fixture in `research/reproduce_ng_findings.py`.

## Migrating an installation

1. Keep the old installation and personal lists as a backup. Install the new package separately and choose a new CYT store.
2. Use a fresh session and narrow capture directory for each trip. Configure Kismet separately; the current adapter needs schema v11 packet records.
3. Add known **advertised addresses** with `cyt known add`. Verify which current address belongs to each of your devices. A privacy address can change; an old entry may stop matching. Do not blindly import all nearby addresses as trusted.
4. Use explicit report windows and thresholds from `docs/RUNTIME.md`. Historical five/ten/fifteen-minute buckets are not translated mechanically.
5. If recording GPS, use `docs/GPS_REPLAY.md`. Preserve original captures and analyze the enriched export separately.

SSID-only exclusions are deliberately absent: a shared network name should not hide every unrelated transmitter using it. Existing personal files are not automatically rewritten or imported. Historic scripts still have their own dependency and permission requirements.

## Backlog and release policy

Close a report as completed only for a concrete delivered behavior. Close explicitly retired behavior as not planned, with a link to its replacement or limitation. Preserve unresolved hardware and capture reports. Superseded contributions should receive credit for useful findings; they were not invalid merely because the architecture changed.

Broad legacy refactors and new legacy UIs will be superseded by this migration path. Narrow fixes that prevent data loss or make migration possible remain reviewable. Historical BlackHat materials are archived descriptions, not current product specifications. Remove the old application in a future versioned release only with an announced migration boundary; do not silently move or delete user data now.
