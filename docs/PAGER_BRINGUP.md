# Connecting a Pager for CYT evaluation

**Status: preparation guide, not a supported Pager installer.** CYT currently reads Kismet v11 databases and normalized JSONL; it does not yet read the Pager's native capture format. The Pi remains the reference deployment.

## What to have ready

- A Wi-Fi Pineapple Pager, a data-capable USB cable and a way to power it during testing.
- The firmware version and the connection method that already works: local web interface, USB networking or SSH.
- The GPS accessory model, if present, and any USB hub or power accessories.
- An owned or consenting test phone/hotspot. A TPMS receiver is optional and is a separate later experiment.

Keep credentials and raw route/device logs local. The issue template asks for versions and sanitized diagnostics, not secrets or other people's complete capture files.

## First connection: establish what the device supports

Record firmware, CPU architecture, available RAM/storage, USB devices, installed capture tools and Python/SQLite availability. Check the GPS device/fix state and confirm which radio interfaces can receive while the management connection remains available. Save the device's current configuration before changing it.

The first session should establish a known working connection and a small capture from the test emitter. It does not require a firmware replacement or a full CYT install. Read-only inspection should precede selecting packages or changing services.

Hak5 documents a USB host, 580 MHz MIPS CPU and 256 MB RAM. Package compatibility and actual resource headroom must be measured on the connected unit. Install added packages to the documented eMMC destination when appropriate; do not bulk-upgrade preinstalled system packages. [Specifications](https://shop.hak5.org/products/pager), [external packages](https://documentation.hak5.org/wifi-pineapple-pager/external-packages).

## Prove the observation path before building the interface

1. Compare a short native capture with a known emitter and, when available, a Pi reference capture. Check frame kinds, source timestamps, band/channel coverage and whether optimized captures omit required headers.
2. Build a small adapter that preserves the core's event-time and source-provenance contract. Replaying the same capture twice must not create new sightings.
3. Qualify GPS fixes with their timestamps, age and accuracy. The receiver's coordinates describe the observer, not another transmitter. Verify whether the connected receiver supplies the fields needed by the existing rules.
4. Measure report memory, CPU load, capture backlog and retained history while vendor services run. Do not shorten history below the intended recurrence window to make RAM usage look acceptable.
5. Add a compact list/details screen and controls. Enable optional vibration only after notification behavior passes the ordinary-route checks.

References: [native capture documentation](https://documentation.hak5.org/wifi-pineapple-pager/wifi-pineapple-commands/wifi_pcap), [GPS documentation](https://documentation.hak5.org/wifi-pineapple-pager/gps), [CYT runtime contract](RUNTIME.md), [GPS replay reference](GPS_REPLAY.md).

## Additional TPMS hardware

The built-in Wi-Fi radio cannot receive conventional 315/433 MHz tire sensors. An external receiver and suitable antenna are required. Sharing USB connectivity with GPS may require a hub; simultaneous two-band reception generally adds a second inexpensive SDR. Measure host power, heat, decoding load and endurance before choosing a carrying arrangement. A USB port alone does not establish SDR software compatibility.

Begin that experiment on the Pi using `rtl_433`. Only bring it to Pager after supported sensor coverage and useful recurrence have been demonstrated. See the [sensor roadmap](ROADMAP.md#next-sensor-experiment-passive-tpms).

## Evidence needed for a supported unit

- A pinned firmware/dependency combination and repeatable installation.
- Capture/replay parity, qualified GPS and visible degraded states.
- Measured runtime, resource use and storage behavior for the intended trip duration.
- Verified restart, disconnect, export, update and rollback behavior without losing user configuration.
- An independent second-unit setup and the route results in the [field validation plan](FIELD_VALIDATION_PLAN.md).

Until those checks are complete, describe the hardware as an experimental prototype. Track results in [issue #37](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37).
