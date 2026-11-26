# Contributing to Chasing Your Tail

CYT's maintained direction is **portable radio awareness**: explainable observations of recurring advertised identifiers. Start with the [roadmap](docs/ROADMAP.md) and [release tracker](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37). Raspberry Pi is the reference target; Pager and additional sensors use the same core through small adapters.

## Useful contributions

- Reproducible bugs with expected and actual behavior.
- Hardware evidence that records the OS/firmware, receiver, capture version and test conditions.
- Small adapters with sanitized fixtures and documented source timestamps, coverage and identifier semantics.
- Usability improvements that make observations, missing coverage and uncertainty easier to understand.

For a substantial new collector or UI, describe the proposal in an issue first so it can fit the shared design. Use the current runtime; the historical scripts follow a separate [legacy policy](docs/LEGACY.md).

## Development

Use Python 3.10 or newer. The core and its tests use the standard library; package metadata is in `pyproject.toml`. The root `requirements.txt` belongs to the historical application.

```console
python -B -m unittest discover -s tests -v
python -B research/evaluate_route_cases.py
```

Run the required suite for changes and relevant replay checks for observation/recurrence changes. Include what was tested and any remaining hardware uncertainty in the pull request. Prefer a small, justified dependency set.

## Observation contract

Keep source event times, session/observer scope and provenance. Re-reading a record must not manufacture a fresh sighting. Keep exact observations distinct from inferred aliases or grouped sensors. Received power is not a reliable distance, and an observer position is not a transmitter position.

An advertised ID, network name or decoder family does not identify a person or establish intent. Describe supported conditions and measured limitations instead of assigning unvalidated threat percentages.

## Sharing evidence

Use synthetic or sanitized fixtures. Preserve the relationships needed to reproduce a bug while removing actual routes, device lists, credentials and unrelated packet contents. Do not commit generated databases, raw field captures or local configuration. Hardware test reports should distinguish a decoded packet, repeatable reception and route-level performance.

Existing issues stay open while their supported behavior or field evidence remains outstanding. A rewrite by itself does not resolve an untested hardware report.
