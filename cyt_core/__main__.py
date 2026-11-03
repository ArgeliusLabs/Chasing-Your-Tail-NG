"""Offline JSONL replay. Python 3.10+ and the standard library only."""
import argparse
import json
from pathlib import Path

from .model import Observation
from .recurrence import summarize


def main():
    parser = argparse.ArgumentParser(description="Replay CYT observations; no radios or network are accessed.")
    parser.add_argument("input", type=Path, help="UTF-8 JSONL observation file")
    parser.add_argument("--at", required=True, type=float, help="UTC Unix timestamp at the end of the replay window")
    parser.add_argument("--ignore", action="append", default=[], metavar="PROTOCOL,MAC")
    args = parser.parse_args()
    try:
        ignored = [item.split(",", 1) for item in args.ignore]
        if any(len(item) != 2 or item[0] not in ("wifi", "ble") for item in ignored):
            raise ValueError("--ignore requires wifi,MAC or ble,MAC")
        observations = []
        with args.input.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    observations.append(Observation.from_dict(json.loads(line)))
                except (TypeError, ValueError, KeyError) as error:
                    raise ValueError(f"line {line_number}: {error}") from error
        print(json.dumps(summarize(observations, at=args.at, ignored=ignored), indent=2, allow_nan=False))
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"cyt_core: {error}\n")


if __name__ == "__main__":
    main()
