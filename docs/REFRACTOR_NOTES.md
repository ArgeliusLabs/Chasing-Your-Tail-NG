# CYT observation core implementation and migration

**Historical first-milestone notes:** the offline design below records the initial 25-test prototype. The development branch has since added packet ingestion, SQLite storage, packaging, persistent exclusions, and a local browser. Use [RUNTIME.md](RUNTIME.md) for the current commands, source contract, tests, and limitations. References below to future storage/UI work describe the earlier milestone, not current feature status.

The new `cyt_core` package is an executable design prototype for portable recurrence awareness. It reads UTF-8 JSON Lines and explains repeated advertised identifiers. It uses Python 3.10 or newer and only the standard library. It has no network calls, radios, UI, credential loading, or import-time filesystem writes.

## Run the prototype

From the NG repository directory:

```console
python -B -m unittest discover -s tests -v
python -B -m cyt_core research/example-route.jsonl --at 1200
python -B -m cyt_core research/example-route.jsonl --at 1200 --ignore wifi,02:00:00:00:00:01
```

The fixture is entirely synthetic. Its timestamps are Unix seconds chosen for deterministic replay, not a real November 2026 route. The first run reports one identifier with three wildcard probes at three separated observer locations. The ignored run reports zero identifiers. Neither result is a conclusion about a person.

Verification on November 3, 2026: all 25 behavioral and CLI tests passed under Python 3.13.11 on Windows. The example replay and all nine baseline reproductions also completed. New Python files parsed successfully, JSON artifacts loaded, and documentation links resolved. Linux and Pager execution are not covered by those results.

The separate baseline audit script has the original repository's `cryptography` dependency because it imports the old analyzer:

```console
python -B research/reproduce_ng_findings.py
```

That script confirms nine old behaviors. It intentionally asserts the audited baseline behavior; it must not be mistaken for the replacement's acceptance suite. It uses a temporary synthetic SQLite database inside `research`, validates the directory scope, and closes/collects handles before cleanup.

## Package responsibilities

| File | Responsibility |
| --- | --- |
| `cyt_core/model.py` | Validate observations, observer positions, address representation, and rule settings |
| `cyt_core/recurrence.py` | Pure, deterministic recurrence analysis within a selected time window |
| `cyt_core/__main__.py` | Read JSONL, report malformed input by line, and output structured JSON |
| `tests/test_recurrence.py` | Behavioral tests for duplicate, timing, GPS, privacy, and recurrence edge cases |
| `tests/test_cli.py` | End-to-end replay, ignore-list behavior, and failure output |

The model supports Wi-Fi probes, beacons, transmitter-header observations, BLE advertisements, and explicitly labeled device summaries. Empty SSID strings are retained as wildcard probes; null means the SSID was not supplied. Summary SSIDs never become freshly observed directed probes.

UTF-8 strings are sufficient for the synthetic fixtures. A production adapter needs a separate raw-byte SSID representation for arbitrary 802.11 SSID bytes, plus safe display text. Do not discard or silently rewrite raw names at capture time.

## Rules implemented

Defaults are prototype settings, not field-calibrated thresholds:

- Analyze the last 1,200 seconds, excluding future events.
- Count observations in distinct 60-second bins, rather than scoring raw packet volume.
- Require at least three bins and a span of 120 seconds to label recurrence.
- Label recurrence across locations only with at least three observer positions separated by more than 250 meters plus both reported accuracy values.
- Use positions only with a two- or three-dimensional fix, accuracy at most 50 meters, and a timestamp within five seconds of the observation.
- Scope every identifier to its session, observer, protocol, and normalized address.
- Deduplicate repeated event keys; reject conflicting records sharing a key.
- Keep changed addresses separate, even when SSIDs or signal strength match.

The output states are `observed`, `recurring`, and `recurring_across_locations`. There is no threat score, probability, confidence interval, follower count, or automated identity association. A fixed AP heard from widely separated observer positions can qualify for the last label: it describes where it was heard, not whether the AP moved. A passenger or companion can qualify too.

Wi-Fi's locally administered bit produces a `locally_administered` label, not proof of rotation or an OUI vendor attribution. BLE address types must be supplied by the source, because the Wi-Fi bit convention is not a substitute for Bluetooth address-type metadata.

An event key currently consists of session, observer, protocol, address, observation time, and kind. It is adequate for this replay contract. A real packet adapter must preserve a capture identifier and source sequence or equivalent provenance before handling simultaneous frames with identical timestamps. Conflicting inputs currently fail visibly instead of choosing one silently.

## What remains before live replacement

This package is not the entire CYT refactor. It demonstrates a small, testable center for the refactor. The remaining work depends on real capture contracts and hardware validation:

1. A capture adapter for one pinned Kismet build, plus source-health events and original source timestamps. Eventbus status is useful, but new-device notifications alone cannot represent recurrence.
2. A CYT-owned SQLite observation store with unique provenance keys, retention, schema migrations, bounded queries, export, and restart recovery. Leave Kismet's database read-only.
3. Historical import of actual packet/data records and GPS snapshots where available. An aggregate `devices` row must remain a summary, with no reconstructed route.
4. A Pager adapter verified against its exact firmware, radio/interface mapping, optimized capture filters, and GPS output.
5. A passive BLE adapter with verified scan behavior, duplicate-report semantics, and supported PHY coverage.
6. A small Pager UI, cooldown-based notifications, and a local session/known-device workflow.
7. Linux/Pi service packaging and OpenWrt/Pager packaging, each with explicit dependencies and diagnostics.
8. Field validation before setting alert thresholds or making detection-rate claims.

The replay CLI currently loads its input into memory, and spatial comparison uses a simple list of anchors. This is appropriate for bounded development fixtures. It is not a claim of bounded memory or sustained throughput on a 256 MB Pager. A live store must query only the active window and cap/aggregate appropriate metadata; measure it before deployment.

No official Pager binary/package is included. No Tkinter window or Kismet process was launched. No existing user data was migrated. The legacy scripts remain available solely as the baseline for the audit and future compatibility decisions.

## Migration without maintaining two competing products

Treat this prototype as a candidate replacement core, not a second permanently supported implementation. First feed it controlled captures alongside the legacy pipeline, inspect differences, and publish the results. Once the adapter and field gates pass, make the new CLI the only supported runtime and archive the old GUI/report generators with a clear migration note.

Before that cutover, correct legacy documentation that presents heuristic percentages as measured accuracy. Replace the fixed credential-test mode and mismatched ignore filenames in a small, separately reviewable change. Review upstream PR 10 rather than recreating its history. Keep optional WiGLE integration in an extra module so local capture and analysis do not depend on credentials or Internet access.

For maintenance, prefer this small module boundary over a plugin framework. Add a second adapter only after the first is tested end to end. Keep test fixtures synthetic or collected with participant permission, and record source versions so future schema changes can be replayed against the same evidence.
