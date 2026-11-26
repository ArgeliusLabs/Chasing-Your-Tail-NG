# CYT development guide

The maintained application is `cyt_core`, a Python 3.10+ standard-library package. Read `README.md`, `docs/RUNTIME.md`, and `docs/PRODUCT_PLAN_2026_11.md` for its current scope. Raspberry Pi is the first deployment target; Pager comes after measured capture and route validation.

## Structure

- `model.py`: validated observations, observer positions, and explicit recurrence rules.
- `wifi.py`, `kismet.py`: minimal frame decoding and incremental Kismet v11 ingestion.
- `store.py`: separate SQLite observation store, atomic checkpoints, retention, known addresses.
- `gps.py`: conservative post-trip joins to a recorded gpsd JSON stream.
- `recurrence.py`: pure, explainable exact-address analysis.
- `__main__.py`: operator commands; `web.py` and `static/`: read-only local dashboard.
- `tests/`: synthetic software contract tests; `research/`: reproducible examples and historical audit.

## Change and validation conventions

Use source event times, explicit session/observer boundaries, and stable source-event provenance. Never create a new observation merely because an unchanged record was polled again. Keep original observations distinct from inferred aliases. Do not turn a MAC address, SSID, received power, observer coordinate, or manufacturer into a person's identity or threat probability.

Run `python -B -m unittest discover -s tests -v`. For route-policy counterexamples, run `python -B research/evaluate_route_cases.py`. Packaging is defined by `pyproject.toml`; the root `requirements.txt` belongs to the historical application. Keep new runtime dependencies small and justified. Hardware claims require hardware evidence, not synthetic fixtures.

Do not include raw route captures, local device lists, credentials, or generated reports in commits. Use synthetic fixtures with clear labels. Keep user configuration and recordings outside the package so updates do not replace them.

The root legacy scripts are retained for migration/audit; they do not call the new core. Follow `docs/LEGACY.md` before changing that code. New behavior belongs in one observation engine with small platform adapters, not another independent surveillance application or UI-specific analyzer.
