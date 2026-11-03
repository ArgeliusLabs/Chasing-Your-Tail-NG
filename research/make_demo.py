"""Generate labeled, synthetic current-time observations for dashboard preview."""
import argparse
import json
from pathlib import Path
import time

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", required=True, type=Path)
args = parser.parse_args()
now = int(time.time())
events = []
for index, times in enumerate(((now - 240, now - 120, now), (now - 20,), (now - 180, now - 60))):
    for timestamp in times:
        events.append({"session": "synthetic-demo", "observer": "demo-observer", "protocol": "wifi",
                       "address": f"02:00:00:00:00:{index + 1:02X}", "observed_at": timestamp,
                       "kind": "probe" if index < 2 else "beacon", "ssid": "" if index == 0 else "Demo network"})
with args.output.open("x", encoding="utf-8") as stream:
    for event in events:
        stream.write(json.dumps(event) + "\n")
print(f"Wrote {len(events)} synthetic observations to {args.output}")
