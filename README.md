# Chasing Your Tail — experimental observation core

CYT is being rebuilt for portable awareness of recurring nearby radios. This development branch publishes the first executable core, its tests, and the research behind the redesign.

**This is an offline prototype, not a complete replacement for the legacy application.** It reads supplied observations. Live Kismet capture, persistent storage, GPS ingestion, the interface, and Pi/Pager deployment still need implementation and validation. Progress and retained community reports are tracked in [issue #37](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37).

## Run the prototype

Use Python 3.10 or newer from the repository root. The core and its tests use only the Python standard library.

```console
python -B -m unittest discover -s tests -v
python -B -m cyt_core research/example-route.jsonl --at 1200
python -B -m cyt_core research/example-route.jsonl --at 1200 --ignore wifi,02:00:00:00:00:01
```

The example is synthetic. It reports one advertised identifier observed at three separated observer positions. The final command excludes that identifier. No radios, network services, WiGLE credentials, or real route data are needed.

## What works today

- Validate and replay Wi-Fi/BLE observation records, including wildcard probes.
- Report recurrence of the same advertised address within a session and observer scope.
- Reject conflicting duplicates and avoid counting identical reimports as new sightings.
- Use only sufficiently fresh, accurate GPS fixes supplied with observations.
- Preserve named SSIDs as data and keep changed addresses separate.
- Produce structured JSON with the observations supporting each result.

The output labels are `observed`, `recurring`, and `recurring_across_locations`. Locations describe where the observer heard a transmission; they do not establish the transmitter's movement. Recurrence is not proof of a person's identity, intent, or following. No measured detection-accuracy claim is made.

## Development and validation

| Resource | Contents |
| --- | --- |
| [Implementation notes](docs/REFRACTOR_NOTES.md) | Observation contract, defaults, limitations, and remaining live work |
| [Capability assessment](docs/CYT_2026_ASSESSMENT.md) | Probe limitations, legacy defects, hardware feasibility, and product direction |
| [Field validation plan](docs/FIELD_VALIDATION_PLAN.md) | Radio, GPS, route, nuisance-alert, and endurance checks |
| [Rewrite tracker](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37) | Community requirements and issue/PR dispositions |

All 25 behavioral and CLI tests passed on Python 3.13.11 on Windows. These are software checks with synthetic data, not hardware or RF validation. The replay CLI loads its fixture into memory; a bounded persistent store is still required for live operation.

## Legacy baseline

The original scripts are retained so the audit remains reproducible against commit `89c88be`. They do not invoke the new core. Their earlier surveillance/accuracy claims are not supported by the prototype or the audit.

The separate baseline reproduction script imports the legacy analyzer and requires its `cryptography` dependency:

```console
python -B research/reproduce_ng_findings.py
```

Those checks reproduce old defects; they are not the replacement's acceptance tests. Historical setup instructions remain available in the [baseline README](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/blob/89c88be994cfc4ea2f7e151b7c5f0f4ac9d9ca5a/README.md).

## Contributions

Small changes with replayable examples are welcome. Existing reports remain open until their behavior is implemented and verified or explicitly deferred with a linked rationale. See [#37](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37) before starting a larger UI, collector, or deployment change.

Released under the [MIT License](LICENSE).
