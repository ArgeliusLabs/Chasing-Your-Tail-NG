# Record GPS on the Pi and join it after a trip

The `geotag` command adds **observer** positions to a JSONL export using a recorded gpsd stream. This is a post-trip validation tool. It is not a live GPS service or a location estimate for another radio.

Use the existing Pi/Kismet kit first. A receiver must already be working with gpsd. The official [gpspipe guide](https://gpsd.gitlab.io/gpsd/gpspipe.html) documents `-w` for JSON and `-B` for unbuffered output. Its [JSON contract](https://gpsd.gitlab.io/gpsd/gpsd_json.html) describes TPV timestamps, fix modes, optional fields, and estimated errors.

## One trip, one observer, one receiver

These examples use a Linux shell and a directory outside the repository. Choose a new trip directory; do not overwrite an earlier recording.

```sh
mkdir -p ~/cyt-data/trip-001
gpspipe -w -B > ~/cyt-data/trip-001/gps.jsonl
```

Leave that running during the trip. In another terminal, ingest the current Kismet capture directory:

```sh
cyt ingest '/path/to/current-trip/*.kismet' --db ~/cyt-data/trip-001/cyt.sqlite3 --session trip-001 --observer pi-01 --follow
```

Kismet and gpsd timestamps must refer to the same UTC clock. Check clock synchronization before departure, record the clock source, and verify drift after return. CYT does not estimate a clock offset or infer a location during a GPS outage. Radio and GPS services are managed separately.

After stopping both recordings cleanly, export and join:

```sh
cyt export --db ~/cyt-data/trip-001/cyt.sqlite3 > ~/cyt-data/trip-001/observations.jsonl
cyt geotag ~/cyt-data/trip-001/observations.jsonl --gps ~/cyt-data/trip-001/gps.jsonl --gps-device /dev/ttyACM0 --session trip-001 --observer pi-01 --output ~/cyt-data/trip-001/located.jsonl > ~/cyt-data/trip-001/join-report.json
```

Replace `/dev/ttyACM0` with the exact `device` value in your TPV records. It is not assumed from the USB port name. The explicit scope must match every observation in the export. A mixed-session store must be separated before joining; supplying a different label does not relabel its events.

Analyze the result with the trip's ending Unix timestamp:

```sh
cyt replay ~/cyt-data/trip-001/located.jsonl --at END_UNIX_SECONDS --window-seconds 3600
```

`END_UNIX_SECONDS` is a placeholder: use the actual end time, not the current time when reviewing an old trip. For a stored report, import into a **new, separate** database. Enriched records retain their original source event IDs; importing them over the raw records in the original store correctly fails as conflicting evidence. Keep the raw export, GPS log, join report and enriched export together. File hashes can document later changes but do not authenticate a receiver or prove an observation was genuine.

## Join rules

- Only the selected device's TPV records contribute positions. Other record classes and explicitly different devices are ignored. A TPV without a device is rejected because its source is ambiguous.
- Times must be ISO 8601 with an explicit timezone and must not go backwards. A malformed line fails the join. Split a log around a clock reset after checking the clocks.
- Partial fields combine only within the **same GPS measurement timestamp**. Coordinates never carry forward into another epoch.
- A qualifying position needs mode 2 or 3, valid coordinates, and a finite positive horizontal error estimate. `eph` is used when present; otherwise both `epx` and `epy` are required and combined with `hypot`. HDOP is not converted to metres by guesswork.
- The latest prior fix may attach for at most five seconds and only with estimated error no greater than 50 metres by default. `--max-fix-age-seconds` and `--max-accuracy-m` change these gates. Future fixes and interpolated positions are not used.
- A no-fix or incomplete epoch blocks use of the previous good fix. An untimed TPV also invalidates the preceding epoch, because the precise outage time is unknown. This conservative behavior can discard usable positions.
- Existing observation positions are preserved. Scope mismatch or invalid input removes the new partial output. Existing output files are never overwritten.
- The GPS reader rejects more than 200,000 lines or a line longer than 65,536 characters. Split large recordings by trip; this bulk join is intended for Pi/desktop review, not a Pager background loop.

gpsd error estimates have variable statistical meaning and are not guaranteed 95% confidence bounds. They help reject poor fixes; they cannot certify route accuracy or remove urban multipath. The report records the error-estimate convention and counts attached, preserved and unlocated observations. A zero attached count can indicate the wrong device, clock mismatch, absent quality fields, outages, or no temporal overlap.

The existing route rule still requires separated observer locations beyond the configured distance plus both stated errors. A fixed AP can be heard from several such locations. The result is evidence of where **you** heard an address, not proof that its transmitter traveled with you.

## Next live milestone

A live adapter must persist receiver identity, source/receipt times, fix quality, outages and clock diagnostics, then associate each observation without modifying already-committed source evidence. Test unplug/replug, indoor loss, delayed messages, reboot and clock corrections on the actual kit before enabling live route notifications. The offline join provides a reproducible reference for that implementation.
