# CYT roadmap

Updated November 26, 2026. **Portable radio awareness: see what keeps showing up along your route.**

CYT records recurring advertised radio identifiers. Its next useful release is a measured Raspberry Pi field demonstrator, followed by a Wi-Fi Pineapple Pager implementation. A hardware connection or a successful demo is not a validated detector of following.

## Available now

The maintained `cyt_core` package includes Kismet v11 Wi-Fi packet ingestion, exact-address recurrence, separate SQLite storage, restart/copy protection, known-address exclusions, a local read-only dashboard and JSON/JSONL exports. Recorded gpsd logs can be joined after a trip with source, time and fix-quality checks.

Seventy automated tests and synthetic endurance runs exercise software behavior. No completed Pi/Pager radio field trial, live GPS collector, native Pager adapter, TPMS collector, BLE collector or notification system is claimed. See the [validation evidence](SOFTWARE_VALIDATION_2026_11.md).

## Build in this order

| Stage | Deliverable | Evidence required before moving on |
| --- | --- | --- |
| 1. Pi capture | Confirm the actual Pi, adapter, OS, Kismet build and GPS; record a controlled trip | Real, sanitized fixtures and a participant log; measured reception, gaps and clock/fix quality |
| 2. Useful trips | Live GPS, source health, service recovery and compact encounter history | Busy captures retain the intended decision window; comparison with unpruned replay; restarts preserve evidence |
| 3. Quiet notifications | Explainable recurrence cards, known-companion exclusions, acknowledgement and cooldown | Held-out ordinary routes establish nuisance rate, missed sightings and notification delay |
| 4. Pager | Native capture adapter, compact screen, controls, optional vibration and GPS | Capture parity with the core; measured memory, processing backlog, battery endurance and recovery |
| 5. Provisioned units | Repeatable install, update/rollback, support and fulfillment | Another person can set up and recover a second unit; a fulfillment arrangement is confirmed |

A small raw-event buffer can erase earlier sightings before a recurrence rule qualifies. Preserve compact time/location evidence with provenance, and compare results with complete replay. Reducing memory alone is not sufficient.

Pager inventory and a bench feasibility check can start as soon as hardware is available. The Pi remains the reference path for capture and route validation. See [Pager bring-up](PAGER_BRINGUP.md), the [field validation plan](FIELD_VALIDATION_PLAN.md) and [release tracker #37](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/issues/37).

## Next sensor experiment: passive TPMS

For driving, tire-pressure sensors are a useful candidate because some direct TPMS protocols broadcast sensor identifiers that can persist across encounters. This is a hypothesis about useful coverage on supported vehicles, not a claim that every car broadcasts a stable identifier. Earlier controlled research demonstrated static identifiers on particular systems. [Original TPMS study](https://static.usenix.org/events/sec10/tech/full_papers/Rouf.pdf).

Start with an RTL-SDR-class USB receiver and suitable antenna on the Pi, using `rtl_433` for decoding. Many conventional systems operate near 315 or 433 MHz. One inexpensive receiver cannot cover both widely separated bands simultaneously; a hopping experiment must record its blind intervals, or two receivers can cover both at once. Existing `rtl_433` decoders cover numerous TPMS families, with JSON output. [Decoder documentation](https://triq.org/rtl_433/), [sensor frequency examples](https://schradertpms.com/sites/default/files/2020-07/2020%20App%20Guide.pdf).

The integration should:

- Introduce sensor identifiers scoped by protocol/decoder, rather than inventing Wi-Fi MAC addresses. Current observations accept only Wi-Fi/BLE address types.
- Preserve receive time, source, tuned band, decoder version, available integrity checks and observer fix quality. A checksum is not authentication.
- Exclude the operator's explicitly enrolled sensors; avoid treating each wheel as a different vehicle.
- Keep raw sightings separate from inferred groups of tires or Wi-Fi/BLE correlations. A sensor ID is not an owner, license plate or guaranteed unique vehicle identity.
- Compare known participant vehicles and ordinary traffic on controlled routes; measure misses and recurrence separately. Do not turn missing reception into an absence claim.

Indirect TPMS systems do not provide wireless wheel-sensor broadcasts. Some newer direct systems use Bluetooth, requiring a different collector and protocol assessment. Transmission intervals and reception vary. [Continental system distinctions](https://cdn.esa.ch/_storage/asset/13548226/storage/master/200686958_Continental_TPMS_Pro_user_manual_EN.pdf), [Melexis Bluetooth TPMS](https://www.melexis.com/en/news/tech-talks/tpms-integrated-by-oems-with-bluetooth-technology).

This experiment can inform the Pi pilot. Pager integration follows a measured benefit and an acceptable receiver/antenna/power footprint; no additional hardware is required for the existing software demo.

## Other research, kept separate

- **Passive BLE:** assess supported advertisements and address behavior as an additional sensor. Import support is not a live collector.
- **Active Wi-Fi:** a lab experiment with owned or consenting devices may measure whether connection-private addresses improve continuity. Modern Apple and Android devices normally use private addresses when connecting, so this is not a general factory-MAC recovery technique. No active collection mode is implemented or enabled. [Apple private addresses](https://support.apple.com/en-us/102509), [Android randomization](https://source.android.com/docs/core/connect/wifi-mac-randomization-behavior).
- **Cross-address inference:** evaluate hypotheses separately with ground truth. Default recurrence continues to use the exact identifier observed; changing addresses are not silently merged.

## Release position

Keep one small observation engine and thin hardware adapters. Publish what was measured: supported sensors, reception conditions, continuity, nuisance alerts, missed sightings and endurance. If useful visibility and manageable nuisance alerts cannot coexist, retain CYT as an observation/research tool instead of claiming a dependable personal-safety appliance.

The [detailed research plan](PRODUCT_PLAN_2026_11.md) contains the Pi/Pager assessment and fulfillment options. This roadmap adds the subsequent TPMS and active-Wi-Fi discussion; those items remain experiments. Historical scripts and claims are covered by the [legacy policy](LEGACY.md).
