# CYT field validation plan

This plan decides whether a portable CYT release is useful and whether its claims match observable evidence. Software unit tests and synthetic replay do not establish phone visibility, identity continuity, or detection of a person following someone.

## Questions that control the product decision

| Question | Experiment | Decision supported |
| --- | --- | --- |
| What proportion of passes produce observable frames? | Known participant passes with a reference collector and synchronized ground truth | Supported phone/radio states and coverage limits |
| How long does an identifier remain useful? | Measure address continuity without trying to assign people from unknown traffic | Minimum useful route/session duration |
| Do multiple bands improve recall enough to justify more hopping? | Repeat the same known-device passes with different documented channel schedules | Pager radio configuration |
| Do empty probes reach the app? | Compare reference captures, native Pager PCAP, and normalized records | Capture/parser correctness |
| Does native optimized capture omit needed associated-client metadata? | Frame-class comparison with reference capture on fixed test channels | Choice of native output versus an additional adapter |
| Does BLE add useful observations without excessive alerts? | Wi-Fi-only and Wi-Fi-plus-BLE ablations on identical routes | Whether BLE belongs in the first release |
| Can stationary or shared-route radios trigger distracting alerts? | Stationary controls, companions, transit, dense AP corridors, and revisited places | Alert rules and wording |
| Do experimental aliases merge different devices? | Same-model phones with participant-recorded ground truth | Whether alias suggestions can be shown at all |
| Does GPS work in the actual carrying position? | Outdoor, vehicle, pocket, building entrance, and indoor segments | GNSS choice, mounting, and degraded-mode design |
| Can the unit run reliably through a full session? | Continuous capture, GPS, screen-off alerts, export, and restart tests | Battery promise, storage policy, and sales readiness |

## Equipment and records

Use a Pager with the intended GPS accessory and a Pi/Kismet reference installation with known compatible receivers. Record firmware, Kismet version and database schema, driver/chipset, enabled bands, channel schedule, device OS/model, phone settings, and collector placement. More radios do not automatically mean complete reference capture; document the reference's own limits.

For participant ground truth, use a timestamped route log and known-device labels under consent. Keep identifying information outside public fixtures. Preserve original captures locally, derive sanitized replay fixtures, and retain a reproducible mapping only for the study. Do not upload route captures or encountered SSIDs to a service by default.

Record the observer's clock source and GPS time/fix quality. Synchronize independent collectors and measure drift. A location is usable for route inference only when its timestamp and accuracy satisfy the chosen rule; “last known fix” is not current position.

## Test matrix

Begin with roughly a dozen consenting devices across several current iPhone and Android models, including at least two pairs of identical models. Add a laptop, ordinary BLE accessory, portable hotspot, and fixed AP. This is a pilot sample, not representative population coverage. Expand based on observed failures and publish the model/OS/state table instead of implying market-wide accuracy.

Test each phone in these states where supported:

- Wi-Fi enabled, unassociated, screen locked and unlocked.
- Associated to a controlled WPA2/WPA3 network with the normal private-address setting.
- Moving away from and back toward a known network.
- A controlled hidden-network configuration, separately labeled as an exceptional case.
- Radio disabled through the full settings interface, low-power mode, and a phone carried but not actively used.
- BLE enabled and disabled, with and without a known accessory.

Use at least these routes:

| Route | Ground truth | Failure to expose |
| --- | --- | --- |
| Stationary desk for an hour | Observer stationary, background APs stable | Duration and packet volume mistaken for following |
| Repeated walk past a fixed AP | Same AP encountered again | Recurrence mistaken for movement of the transmitter |
| Participant on a parallel route | Known radio genuinely remains nearby | Useful recurrence missed |
| Companion traveling alongside | Benign co-travel | Intent incorrectly inferred from a valid recurrence |
| Bus or train segment | Many benign shared-route radios | Co-occurrence groups and escalating false threat labels |
| Busy street with repeated phone models | Distinct devices | False alias merges |
| Route with indoor GPS loss | Known observer path with unavailable fixes | Stale fixes becoming fictitious locations |
| Two separated appearances with a long gap | Intermittent visibility | First/last span mistaken for continuous presence |

Freeze the proposed rules before evaluating held-out routes. Keep development and evaluation runs separate. Do not tune thresholds on every “test” result and then report that same set as independent evidence.

## Measures to publish

Separate four layers of performance:

1. **Visibility:** fraction of known passes with any observed transmission, broken down by phone state and protocol.
2. **Continuity:** fraction of observation windows retaining the same advertised identifier; experimentally inferred links reported separately.
3. **Recurrence:** correct repeated-identifier events, missed observable recurrence events, and false groupings under known ground truth.
4. **User experience:** nuisance notifications per route-hour, alert delay, battery life, GPS-qualified time, restart behavior, and storage growth.

Include denominators and missed cases. “No alert” can mean no emission, wrong channel, capture outage, identity rotation, a threshold not reached, or absence. Do not collapse those explanations into a reassuring conclusion.

For experimental alias links, publish false-merge and missed-link rates, with same-model controls and dense-environment results. Preserve every original address record so a bad link can be removed without corrupting the observations.

Measure RSSI as received power only. Do not validate distance estimates by comparing them with an assumed radio range. Use measured positions if distance or ranging is ever evaluated.

## Proposed pilot gates

These are proposed engineering acceptance targets, not achieved results:

| Gate | Target |
| --- | --- |
| Data integrity | Replay never multiplies unchanged events; source times and provenance survive export/restart |
| Position integrity | Missing, stale, poor, or unmatched fixes cannot create route locations |
| Capture contract | Every supported event kind and band has a verified fixture from the pinned hardware configuration |
| Status honesty | Capture failure is distinguishable from an active collector hearing nothing; no “safe” or “all clear” state |
| Nuisance alerts | Initial target no more than one actionable recurrence notification per two hours on agreed control routes, excluding explicit user-requested inspection |
| Useful recurrence | Initial target at least 80% recall of predeclared qualifying recurrence events for identifiers that the reference shows remained observable |
| Endurance | Initial target four hours with GPS and intended radios, including screen-off operation; otherwise revise the promised session length or power design |
| Recovery | Controlled battery loss, full storage, database lock, source restart, and GPS unplugging do not fabricate evidence or silently stop status reporting |
| Packaging | A second person can install, start, export, update, and recover using only the supplied instructions |

The conditional recall target is intentionally not “80% of all phones” or “80% of followers.” Report visibility and continuity alongside it so the condition cannot hide undetectable devices.

A small pilot cannot validate a very low false-alert rate. Report route-hours, participant counts, and uncertainty rather than claiming a universal rate after a few successful demonstrations. If the nuisance-alert and visibility results make portable awareness unhelpful, release a transparent research recorder and stop the consumer safety-device sales plan.

## Pager-specific bench checks

Check radio-to-interface mapping on the actual firmware. Exercise each supported band on a controlled channel, compare native Recon and optimized PCAP output, and record which frame classes are present. Check whether enabling capture or a payload changes channel hopping. Repeat after a firmware update before extending support to that version.

Verify passive BLE scan settings at the controller and, when possible, with an independent receiver. Bluetooth classic inquiry and active BLE scanning must not be mislabeled as receive-only. Account for management-AP and client-mode transmissions separately from the collection mode.

Measure memory, CPU, flash growth, event ingestion backlog, packet/drop counters where available, GPS time-to-fix, fix age, and energy draw. Test with high event volume as well as an empty room. Confirm haptic alerts while the display is off and that stopping a session releases resources without interfering with the vendor UI.

Before a paid pilot, repeat the complete provisioning and recovery process on a second unit. A successful development unit is not yet a reproducible product.
