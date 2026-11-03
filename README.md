# Chasing Your Tail — experimental portable observation runtime

CYT reports recurring nearby **advertised radio identifiers**. Modern phones often send wildcard probes and change addresses. CYT counts observed transmissions without requiring remembered network names and keeps changing addresses separate.

The repository now includes a Kismet packet adapter, persistent storage, a CLI, and a local browser dashboard, merged in [PR #38](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/pull/38). It is an **experimental alpha**, with synthetic software tests and no completed Pi/Pager field validation. The original scripts remain separate. Follow the [rewrite tracker](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37) for the remaining work.

## Try it without hardware

Python 3.10 or newer is required. The runtime and tests use only the standard library. Run these commands from the repository root:

```console
python -B -m unittest discover -s tests -v
python -B -m cyt_core replay research/example-route.jsonl --at 1200
python -B research/make_demo.py --output demo-observations.jsonl
python -B -m cyt_core import-jsonl demo-observations.jsonl --db demo.sqlite3
python -B -m cyt_core serve --db demo.sqlite3
```

Open **http://127.0.0.1:8765**. The generated observations are labeled `synthetic-demo` and use current timestamps. The fixed replay fixture uses old timestamps for deterministic tests. The demo generator refuses to overwrite an existing file; use a new output name for another demo. Keep demo and real captures in separate stores.

No WiGLE account, API credentials, desktop toolkit, or network connection is needed for this demo. Stop the server with Ctrl+C. For an installed `cyt` command, create a virtual environment and run `python -m pip install --no-deps .`; see [setup and operation](docs/RUNTIME.md).

## Read a Kismet capture

The adapter targets **Kismet database schema v11**, based on `kismet-2026-10-R1`, with packet logging enabled. Kismet must already be configured and capturing; CYT does not configure radios or start Kismet.

```console
python -B -m cyt_core ingest /path/to/capture.kismet --db cyt.sqlite3 --session trip-001 --observer pi-01
python -B -m cyt_core report --db cyt.sqlite3 --window-seconds 1200
python -B -m cyt_core status --db cyt.sqlite3
```

For a growing capture directory, run this collector in one terminal and the dashboard in another:

```console
python -B -m cyt_core ingest "/path/to/captures/*.kismet" --db cyt.sqlite3 --session trip-001 --observer pi-01 --follow
python -B -m cyt_core serve --db cyt.sqlite3
```

Use paths for your machine. Quote the glob so newly rotated files can be discovered. Reuse the session name when restarting the same trip; use a new name for a new trip. The dashboard binds only to `127.0.0.1` and offers read-only access. An SSH tunnel can provide access from another computer; see the runtime guide.

## What this version does

- Reads supported Wi-Fi probe requests, beacons, and data headers from packet records, using their source timestamps.
- Preserves empty and binary SSIDs. Named probe strings remain optional evidence.
- Commits observations and ingestion checkpoints together. Restarts and unchanged inputs do not manufacture sightings.
- Follows growing and rotated captures; reports missing, unsupported, malformed, and stale input.
- Stores observations in a separate SQLite database, with a configurable row cap and follow-mode age retention.
- Persists normalized known-address exclusions through `cyt known` commands.
- Produces JSON reports and JSONL exports; displays results in a small local dashboard.

The output labels are `observed`, `recurring`, and `recurring_across_locations`. Positions describe where the observer heard a transmission. Recurrence does not prove device identity, a person's identity, intent, or following. An empty display does not establish safety or complete capture coverage.

**GPS and BLE:** validated positions and BLE observations can be supplied through JSONL. The Kismet adapter currently ingests Wi-Fi packets only and supplies no qualified GPS fixes: its packet table lacks the fix time and accuracy needed by CYT's route rules. Live GPS integration, BLE capture, and Pager deployment remain work to do.

## Development and evidence

| Resource | Purpose |
| --- | --- |
| [Runtime guide](docs/RUNTIME.md) | Installation, commands, storage, source contract, troubleshooting, and limits |
| [Capability assessment](docs/CYT_2026_ASSESSMENT.md) | Phone privacy behavior, legacy audit, hardware feasibility, and product direction |
| [Field validation plan](docs/FIELD_VALIDATION_PLAN.md) | Radio, GPS, route, nuisance-alert, and endurance checks |
| [Earlier core design](docs/REFRACTOR_NOTES.md) | Original replay milestone and migration rationale |
| [Rewrite tracker](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37) | Community requirements and remaining release gates |

All 53 tests and the installation smoke checks passed on Windows and Linux with Python 3.10 and 3.13 for the merged runtime ([CI run](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/actions/runs/41714526125)). The tests use synthetic captures, including active SQLite WAL writes, restart, rollback, rotation, duplicate input, retention, event-time windows, and HTTP behavior. They do not measure RF detection performance.

## Legacy code and contributions

The original scripts remain for migration and audit reproducibility; they do not call this runtime. The old `requirements.txt` belongs to those scripts. The separate `research/reproduce_ng_findings.py` reproduces legacy defects and requires the legacy `cryptography` dependency. It is not the new runtime's acceptance suite.

Community reports informed the rewrite, including the ignore-file proposal in [PR #8](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/pull/8). Small changes with replayable examples are welcome. Existing issues close when their supported behavior is delivered and verified or explicitly deferred with a rationale. See the tracker before beginning a second UI or collector implementation.

Released under the [MIT License](LICENSE).
