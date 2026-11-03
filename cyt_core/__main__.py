"""CLI for replay, Kismet ingestion, reports, and a local browser view."""
import argparse
import glob
import json
from pathlib import Path
import signal
import sqlite3
import sys
import time

from .kismet import ingest
from .model import Observation, Rules, number
from .recurrence import summarize
from .store import Store


def output(value):
    print(json.dumps(value, allow_nan=False), flush=True)


def replay(path):
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                yield Observation.from_dict(json.loads(line))
            except (TypeError, ValueError, KeyError) as error:
                raise ValueError(f"line {line_number}: {error}") from error


def ignores(values):
    result = [item.split(",", 1) for item in values]
    if any(len(item) != 2 or item[0] not in ("wifi", "ble") for item in result):
        raise ValueError("--ignore requires wifi,MAC or ble,MAC")
    return result


def analyze_options(parser):
    parser.add_argument("--at", type=float, help="UTC Unix seconds; default: current time")
    parser.add_argument("--window-seconds", type=float, default=1200)
    parser.add_argument("--ignore", action="append", default=[], metavar="PROTOCOL,MAC")


def parser_for_cli():
    parser = argparse.ArgumentParser(description="CYT: portable awareness of recurring advertised radio identifiers.")
    sub = parser.add_subparsers(dest="command", required=True)
    read = sub.add_parser("replay", help="analyze observation JSONL without creating a database")
    read.add_argument("input", type=Path)
    analyze_options(read)
    capture = sub.add_parser("ingest", help="read Kismet v11 packet databases once or follow rotating files")
    capture.add_argument("inputs", nargs="+", help="paths or quoted glob patterns")
    capture.add_argument("--session", required=True, help="trip/run name; reuse when restarting that run")
    capture.add_argument("--observer", required=True, help="name of the physical observer")
    capture.add_argument("--follow", action="store_true")
    capture.add_argument("--poll-seconds", type=float, default=2)
    capture.add_argument("--batch-size", type=int, default=1000)
    capture.add_argument("--retention-seconds", type=float, default=604800, help="follow mode: seven days by default, plus the row cap")
    load = sub.add_parser("import-jsonl", help="atomically import validated observation JSONL")
    load.add_argument("input", type=Path)
    report = sub.add_parser("report", help="analyze stored observations in an event-time window")
    analyze_options(report)
    status = sub.add_parser("status", help="show capture freshness and skip counts")
    status.add_argument("--at", type=float)
    known = sub.add_parser("known", help="persist exact advertised addresses to exclude from reports")
    known.add_argument("action", choices=("list", "add", "remove"))
    known.add_argument("--protocol", choices=("wifi", "ble"))
    known.add_argument("--address")
    known.add_argument("--label", default="")
    prune = sub.add_parser("prune", help="delete observations older than an explicit UTC cutoff")
    prune.add_argument("--before", type=float, required=True)
    export = sub.add_parser("export", help="stream retained observations as JSONL to stdout")
    export.add_argument("--since", type=float, default=0)
    serve = sub.add_parser("serve", help="read-only dashboard at http://127.0.0.1:8765")
    serve.add_argument("--port", type=int, default=8765)
    for command in (capture, load, report, status, known, prune, export, serve):
        command.add_argument("--db", required=True, type=Path, help="CYT-owned SQLite file (never the Kismet file)")
        command.add_argument("--max-events", type=int, default=100000, help="retained observation cap on writes")
    return parser


def collect(args, store):
    if not 1 <= args.batch_size <= 10000:
        raise ValueError("batch_size must be between 1 and 10000")
    if not args.session.strip() or not args.observer.strip():
        raise ValueError("session and observer must be nonempty")
    if number(args.poll_seconds, "poll_seconds") < .1:
        raise ValueError("poll_seconds must be at least 0.1")
    if number(args.retention_seconds, "retention_seconds") <= 0:
        raise ValueError("retention_seconds must be positive")
    stopped = False

    def stop(*_):
        nonlocal stopped
        stopped = True

    previous_handler = signal.signal(signal.SIGTERM, stop)
    try:
        while not stopped:
            paths = sorted({str(Path(p).resolve()) for pattern in args.inputs for p in glob.glob(pattern)})
            if not paths:
                if not args.follow:
                    raise ValueError("no Kismet files match the supplied paths")
                output({"state": "waiting_for_capture", "inputs": args.inputs})
            backlog, errors = False, []
            for path in paths:
                if stopped:
                    break
                if Path(path) == args.db.resolve():
                    raise ValueError("the CYT store cannot also be a Kismet input")
                try:
                    result = ingest(path, store, session=args.session, observer=args.observer,
                                    batch_size=args.batch_size,
                                    retention_before=time.time() - args.retention_seconds if args.follow else None)
                    output(result)
                    backlog |= result["more"]
                except (OSError, ValueError, sqlite3.Error) as error:
                    errors.append({"path": path, "error": str(error)})
            if errors:
                print(json.dumps({"state": "capture_error", "errors": errors}), file=sys.stderr, flush=True)
                if not args.follow:
                    return 2
            if not args.follow and not backlog:
                break
            deadline = time.monotonic() + (args.poll_seconds if not backlog or errors else .1)
            while not stopped and time.monotonic() < deadline:
                time.sleep(min(.1, max(0, deadline - time.monotonic())))
    finally:
        signal.signal(signal.SIGTERM, previous_handler)
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = {"replay", "ingest", "import-jsonl", "report", "status", "known", "prune", "export", "serve"}
    if argv and not argv[0].startswith("-") and argv[0] not in commands:
        argv.insert(0, "replay")  # Original prototype invocation remains valid.
    parser = parser_for_cli()
    args = parser.parse_args(argv)
    try:
        if args.command == "replay":
            output(summarize(replay(args.input), at=args.at if args.at is not None else time.time(),
                             rules=Rules(window_seconds=args.window_seconds), ignored=ignores(args.ignore)))
            return 0
        if args.command == "ingest" and any(args.db.resolve() == Path(p).resolve()
                for pattern in args.inputs for p in glob.glob(pattern)):
            raise ValueError("the CYT store cannot also be a Kismet input")
        with Store(args.db, max_events=args.max_events) as store:
            if args.command == "ingest":
                return collect(args, store)
            if args.command == "import-jsonl":
                count = 0
                with store.db:
                    for event in replay(args.input):
                        count += store.insert(event)
                    removed = store.trim()
                output({"inserted": count, "removed": removed})
            elif args.command == "report":
                output(store.report(at=args.at if args.at is not None else time.time(),
                                    rules=Rules(window_seconds=args.window_seconds), ignored=ignores(args.ignore)))
            elif args.command == "status":
                output(store.status(at=args.at))
            elif args.command == "known":
                output(store.known(args.action, args.protocol, args.address, args.label))
            elif args.command == "prune":
                with store.db:
                    removed = store.trim(args.before)
                output({"removed": removed})
            elif args.command == "export":
                number(args.since, "since")
                for row in store.db.execute("SELECT body FROM observations WHERE observed_at >= ? ORDER BY observed_at, identity", (args.since,)):
                    print(row[0])
            elif args.command == "serve":
                from .web import serve
                serve(store, port=args.port)
    except KeyboardInterrupt:
        return 130
    except (OSError, ValueError, TypeError, sqlite3.Error) as error:
        parser.exit(2, f"cyt_core: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
