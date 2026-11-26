# CYT setup

Start with the **experimental observation runtime**. Python 3.10 or newer is required. Development targets the existing Raspberry Pi kit first; a Pager port is a later hardware milestone.

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --no-deps .
.venv/bin/cyt replay research/example-route.jsonl --at 1200
```

This replay needs no radio, GPS, WiGLE account, or API key. The build may download setuptools. On Windows, use `python` and `.venv/Scripts/python` / `.venv/Scripts/cyt` instead.

For capture, Kismet must already be running with compatible Wi-Fi hardware and packet logging enabled. CYT reads Kismet schema v11 captures; it does not install Kismet or configure radios.

```sh
.venv/bin/cyt ingest '/path/to/captures/*.kismet' --db cyt.sqlite3 --session trip-001 --observer pi-01 --follow
```

In another terminal:

```sh
.venv/bin/cyt serve --db cyt.sqlite3
```

Open `http://127.0.0.1:8765`. For a remote Pi, use the SSH tunnel in the operator guide. A read-only local dashboard and recurrence reports are available; measured phone visibility, live GPS, notifications, and a supported Pi/Pager appliance remain release gates.

- [Installation, commands, retention and troubleshooting](docs/RUNTIME.md)
- [Join an observer GPS log after a trip](docs/GPS_REPLAY.md)
- [Pi-first product and validation plan](docs/PRODUCT_PLAN_2026_11.md)
- [Legacy migration policy](docs/LEGACY.md)

The root `requirements.txt`, `config.json`, Tkinter UI, WiGLE credentials and `surveillance_*` scripts belong to the historical application. They are not prerequisites for the new runtime. The former BlackHat setup instructions and unsupported detection/security claims remain available in Git history for reference.
