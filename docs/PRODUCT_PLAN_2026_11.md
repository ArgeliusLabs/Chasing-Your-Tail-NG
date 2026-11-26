# CYT: Pi-first recovery plan and Pager product path

Research and repository review: November 26, 2026. First target: the existing Raspberry Pi kit. Second target: Wi-Fi Pineapple Pager with GPS. Status: experimental alpha; no completed radio field trial.

## Decision

**Continue CYT as an explainable recorder of recurring nearby radios. Do not promise dependable detection of a person following the user.** There is still useful observable information, especially from persistent hotspots, vehicle access points and some associated radios. There is no general passive replacement for remembered-network disclosure or a stable phone identity when those are no longer transmitted.

The strongest new release would demonstrate a measured capability: “this advertised radio address was heard at these times and points along my route.” It should show capture/GPS gaps and ordinary explanations alongside the recurrence. A validated recorder and a reproducible benchmark would be a stronger contribution than another surveillance score or a cosmetic Pager port.

Build the Pi reference system, measure its usefulness, then package the successful subset on Pager. Stop the consumer alert-device plan if useful visibility and manageable nuisance alerts cannot coexist. The software can still be worthwhile as an open research and incident-timeline tool.

## What changed, and what can replace it

Two separate losses matter. A wildcard probe reveals no requested network name. Address rotation separately breaks continuity. Counting wildcard probes repairs the first omission in a collector; it does not solve the second. Associated and hotspot addresses may persist within a connection/session, without being permanent device identities. Apple's documentation describes hidden-network exceptions, private connection addresses and hotspot address changes. Android documents persistent and nonpersistent private-address modes. Behavior varies by model, OS, network and device state. [Apple Wi-Fi privacy](https://support.apple.com/en-ca/guide/security/sec31e483abf/web), [Android randomization behavior](https://source.android.com/docs/core/connect/wifi-mac-randomization-behavior).

| Signal | Useful capability | Priority and limit |
| --- | --- | --- |
| AP/hotspot beacons and advertised transmitter address | Repeated sightings of an emitting hotspot or vehicle AP | First: often observable repeatedly while active; fixed infrastructure and benign companions also recur |
| Associated-client/data transmitter headers | Continuity while an address remains stable and its channel is captured | First: encrypted payloads need not be read; an AP transmitter is not the client behind it |
| Wildcard probe source and timestamp | Short-session recurrence without any SSID | First: useful until rotation, sparse scanning or silence breaks the sequence |
| Directed probe name, when actually present | Optional context for that specific transmission | Retain: no remembered-history reconstruction or origin inference |
| BLE advertisements | Additional observable accessories, tags and other emitters | Second sensor: requires a verified passive collector and its own address-type handling |
| GPS, time and capture coverage | Where the observer heard a radio; whether gaps are interpretable | Essential supporting evidence, not a radio identity |
| RSSI history | A received-power trend for a specific receiver | Supporting display only; no reliable metres, bearing or person identification |
| Capability/IE signatures, timing and upstream aliases | Research hypotheses about related addresses | Separate experiment; never silently merge exact observations |

An SSID can be shared by unrelated APs. Manufacturer/capability information often identifies a product family. A locally administered address is not proof that an address actually rotated. Repeated counts do not equal repeated people. None of these is an appropriate identity key by itself.

Apple also randomizes scan sequence numbers when changing randomized addresses on supported devices. Thus sequence continuity is not a universal recovery path. Bluetooth private-address resolution depends on an identity resolving key; a generic passive receiver does not automatically have it. [Apple scan/frame privacy](https://support.apple.com/en-ca/guide/security/secb9cb3140c/web), [Bluetooth architecture, privacy feature](https://www.bluetooth.com/wp-content/uploads/Files/Specification/HTML/Core_v7.0/out/en/architecture%2C-change-history%2C-and-conventions/architecture--arch-.html).

## Research worth doing, without overstating it

Kismet now offers optional Wi-Fi and BLE address linking. Its documentation explicitly treats those relationships as best guesses, retains separate address records, and notes false links, missed links and no linking across runs. Some documented BLE methods are newer than the `2026-10-R1` tag. Pin an actual build and record which methods it contains before testing. Evaluate upstream relationships in an opt-in research view with ground truth, rather than writing a competing identity engine into CYT. Leave them out of default alerts. [Kismet randomized addresses](https://www.kismetwireless.net/docs/readme/configuring/randomized_macs/).

A June 2026 study combines probe capabilities, timing and spatial information for clustering. Its spatial data are simulated; devices are static in a small modeled area and its stronger spatial scenario uses three sniffers. Those results do not establish reliable tracking by one moving Pager. This is a useful experiment design reference, not a product accuracy figure. [Can Machine Learning Break Wi-Fi Privacy?](https://arxiv.org/html/2606.25788v1).

BLE tracker awareness is a plausible separate module, but generic BLE recurrence should not be advertised as equivalent to phone-platform unwanted-tracker detection. Android's supported tracker alerts use a specific ecosystem and can still have benign co-travel explanations. Keep built-in phone protections enabled; a future CYT module would complement them. Do not assume BLE support gives Pager UWB ranging or cellular-device detection. [Android unknown tracker support](https://support.google.com/android/answer/13658562?hl=en).

Do not prioritize deauthentication, rogue APs, forced reconnects, Bluetooth inquiry, or active scan requests to recover missing identifiers. They change the passive product and the experiment. Likewise, WiGLE lookup cannot establish who owns a phone or where a person came from. A time-window incident log can corroborate that a transmission was heard; it cannot identify an intruder merely from a network name.

## The next useful behavior

The present engine can report exact-address recurrence in time bins and across separated observer positions. The new `research/evaluate_route_cases.py` makes eleven scenarios replayable, including failures and ambiguous cases. A companion and a fixed AP heard over several points can yield the same output as a portable hotspot. That is a property of the available evidence, not a bug a confidence percentage can remove.

The next alert experiment should add **encounters**: distinct periods of observation separated by an absence that capture coverage can support. Do not call a hopping-radio miss an encounter ending. Preserve the first/last timestamps, number of occupied bins, actual gaps, frame kinds, source radios, channel coverage and fix quality. Never convert first-to-last span into continuous presence.

Use these behaviors in order:

1. A quiet list of recently observed addresses, with “known to me” exclusions and a clear start/end trip control.
2. A review card when an unfamiliar exact address recurs across usable route segments. Explain the observations and allow “known companion” or “dismiss for this trip.” Keep observer positions visible as observer positions.
3. Only after the control-route gate passes, an optional single vibration on a new qualifying encounter. Add cooldown, acknowledgement and explicit capture/GPS-degraded states. Repeated frames must not repeat the alert.
4. An exportable trip timeline showing observations and missing coverage. A map is a view of the user's route and hearing locations, not a reconstructed suspect route.

Example proposed copy: **“Radio seen again: 3 observation areas over 8 minutes. Last heard 12 seconds ago. This can include companions or fixed transmitters.”** Avoid “tail confirmed,” threat percentages, and “all clear.” These notifications and encounter logic are planned, not shipped in this milestone.

## Pi reference deployment

Reuse the actual Pi, supported monitor-mode Wi-Fi adapter, GPS receiver and battery already available. The exact Pi model, adapter chipset, driver, OS and GPS model have not been confirmed in this review; do not buy replacements based on an assumed inventory. Start on 2.4/5 GHz only if the existing adapter supports them reliably. Test a second receiver or 6 GHz only when measured coverage justifies the added power and scheduling complexity.

There is another potentially useful recovery path for existing hardware: Kismet's October 2026 USB userspace capture source supports selected MediaTek and Realtek adapters without relying on the host's normal Wi-Fi kernel driver. That may help an older Pi installation with a troublesome driver. Verify the exact chipset, USB permissions, power and shipped Kismet build; the documentation distinguishes tested devices from ones using similar untested driver code. Treat this as a bench option before buying another adapter, not a compatibility promise. [Kismet USB userspace capture](https://www.kismetwireless.net/docs/readme/datasources/wifi-usb-userspace/).

Keep Kismet responsible for radio collection, gpsd for the receiver, and CYT for normalized events, storage, analysis and presentation. Each service should have a visible health state. A working management connection does not prove the capture radio is listening to the required channel.

The software now offers:

- Incremental Kismet v11 packet reads, wildcard probes, beacons and data transmitter headers.
- Separate SQLite storage, atomic checkpoints, repeat/copy/restart protection and bounded retained rows.
- Exact known-address exclusions, JSONL export, explicit report thresholds and a local read-only browser.
- Post-trip GPS joins with device/scope checks, fix-age/error gates, outage barriers and no interpolation. See [GPS replay instructions](GPS_REPLAY.md).

The first real session should collect a controlled hotspot, a same-route companion, a fixed AP and two phones in ordinary locked/unassociated states. Record GPS alongside the capture. Compare the retained observations against the capture and participant log, including all missed sightings. This determines whether to adjust capture settings or detection policy; it avoids mistaking missing packets for a scoring problem.

Then add a live GPS adapter and service supervision, using the offline join as a reference. Keep the initial display on the existing browser. Add another UI only after the data path is dependable. Kismet and CYT retention are separate: bounding CYT does not bound the original packet files.

## Pager feasibility and physical product

The Pager supplies a 480×222 display, controls, vibration, a 2,000 mAh battery, Wi-Fi radios, Bluetooth and USB host in an approximately 87×62×24 mm, 131 g base unit. It has a 580 MHz MIPS processor, 256 MB RAM and 4 GB eMMC. These make a compact independent recorder plausible, but memory, energy and capture contention need measurement. A GPS accessory and antenna add to the base dimensions. [Official Pager specifications](https://shop.hak5.org/products/pager).

The newer **Glytch GPS Mod Pro** advertises L1/L5 reception, an active external antenna and USB-C power/data passthrough. These are useful for a portable recorder and external power. They do not establish indoor fixes, a particular route accuracy, or another transmitter's location. Test its real carrying position against the existing receiver before choosing the paid bundle. [GPS Mod Pro](https://shop.hak5.org/products/glytch-gps-mod-pro), [Pager GPS configuration](https://documentation.hak5.org/wifi-pineapple-pager/gps).

Hak5 documents OpenWrt package installation to the eMMC and warns that the smaller root overlay can fill. Its Python example uses the eMMC destination; firmware changes can affect package compatibility. Keep the core standard-library-only, pin supported firmware and dependencies, and avoid bulk upgrades of the underlying system. Python/SQLite availability and footprint must be checked on the target unit. [External packages](https://documentation.hak5.org/wifi-pineapple-pager/external-packages).

Use a small Pager adapter rather than assuming the Pi's full Kismet stack should move unchanged. The native optimized PCAP command trims data; compare its frame classes, timestamps and bands with a reference capture before selecting it. The current CYT runtime does not yet read native Pager PCAP directly. [Native PCAP contract](https://documentation.hak5.org/wifi-pineapple-pager/wifi-pineapple-commands/wifi_pcap).

There is already a native mapping/wardriving payload, **NetRider**, whose current launcher requires firmware 2.0.0 or newer. It is evidence that GPS, offline route context and the display can coexist. It is not evidence of a stable integration API or permission to redistribute its implementation. Start CYT with a compact list/details view and haptics. Evaluate NetRider coexistence before building a second map stack. [Official payload README at the reviewed revision](https://github.com/hak5/wifipineapplepager-payloads/blob/08a6fb09544a385baee8bda381f4025de1bb979e/library/user/reconnaissance/NetRider/README.md).

Existing independent CYT Pager projects also mean that “CYT on a Pager” alone is not a novel claim. The earlier assessment reviews them; their code was not copied. Recheck licenses before any reuse. Different capture implementations must pass the same replay contract, even when their front ends differ.

| Existing project | Lesson for CYT | Boundary |
| --- | --- | --- |
| [pineapple_pager_cyt](https://github.com/pineapple-pager-projects/pineapple_pager_cyt) | On-device list, controls, headless operation and vibration are already demonstrated in another implementation | Its threat-score and clustering interface does not validate identity or intent; no root license was reported by GitHub on this review date |
| [chasing-your-tail-pager](https://github.com/tschakram/chasing-your-tail-pager) | Compare lifecycle and radio integration against our adapter contract | Verify actual receive-only behavior; do not equate a project's passive description with measured radio behavior; no root license was reported by GitHub on this review date |
| [AirGuard](https://github.com/seemoo-lab/AirGuard) | Study unwanted-tracker UX, known-device exclusions and notification cooldown | Android tracker application, not a generic Wi-Fi identity detector or a Pager drop-in; published under Apache-2.0 |

The two Pager repositories had no newer pushes than the versions examined in the earlier assessment. AirGuard's [reviewed notification worker](https://github.com/seemoo-lab/AirGuard/blob/d515c534be7aac370de33e7bae0136a7b995e0cf/app/src/main/java/de/seemoo/at_tracking_detection/detection/TrackingDetectorWorker.kt) uses observation duration, location count, exclusions and notification spacing. Those are useful design references, not thresholds to transplant into a different receiver and radio population. Its implementation was read for comparison; no code was copied.

Proposed Pager screen: session/GPS/capture state at the top, up to five recent recurrence entries, and one-button details/acknowledgement. Store bounded recent events and export older trips. Test a conservative event cap first instead of copying the desktop maximum. No desktop toolkit, dataframe stack, machine-learning runtime or internet map dependency belongs in the first appliance.

There is now a measured software reason for that cap: a 100,000-event synthetic report with 1,000 identifiers dropped from about 144 MB to 91 MB of traced Python allocations after removing a duplicate in-memory JSON window. With 100,000 distinct identifiers it still used about 207 MB. These desktop figures exclude some native memory and are not Pager RAM measurements. The [validation report and reproducible benchmark](SOFTWARE_VALIDATION_2026_11.md) make the remaining constraint explicit.

**Do not solve memory by shrinking history until recurrence becomes impossible.** Approximate retained history is row cap divided by accepted rows per second. At 100 rows/second, a 10,000-row cap holds about 100 seconds, less than the default 120-second minimum span; a busy beacon environment can therefore erase the earlier encounter before a report qualifies. The next storage milestone must measure this tradeoff and retain compact per-address/time/location evidence separately from bounded raw metadata. Keep counts, first/last source times and provenance to the original capture; do not relabel summaries as fresh packet observations. Compare summary-based results against unpruned replay before enabling that path. A smaller buffer alone is not a usable Pager design.

## Milestones and exit evidence

These are work packages and proposed acceptance criteria, not promised calendar dates or achieved hardware results.

| Milestone | Deliverable | Exit evidence |
| --- | --- | --- |
| 0 — repository reset | Current setup, one core, migration policy, triaged backlog, research and reproducible counterexamples | Automated tests and installation checks; legacy claims clearly separated |
| 1 — Pi capture truth | Known kit inventory; real per-frame timestamps and source/band checks; simultaneous GPS log | Every supported frame kind has a sanitized real fixture; empty probes survive end to end; drift and loss recorded |
| 2 — Pi route pilot | Live GPS/health, retained-history diagnostics, compact evidence design, exact-address encounter review, replayable route dataset | Busy-scene retention preserves the intended decision window; held-out controls and known-radio routes publish nuisance rate, visibility, continuity and latency separately |
| 3 — Pager parity | Pinned firmware adapter, compact UI/haptics, storage limits, recovery/export | Same observations produce same engine results; actual CPU/RAM/backlog/flash and GPS behavior measured |
| 4 — paid pilot | Reproducible installation, update/rollback, support process, provisioned unit checklist | Another person sets up/updates/recovers it; full intended session endurance passes; fulfillment terms confirmed |

Start with a small controlled pilot, then extend the existing [field validation plan](FIELD_VALIDATION_PLAN.md). Freeze rules before held-out trials. Include walking and driving, dense and sparse environments, fixed AP corridors, public transit, companions, GPS loss and radio restarts. Use several current phone models and same-model pairs. State every OS, firmware, adapter and phone-state condition.

Proposed gates remain at least 80% recurrence recall **among predeclared events whose identifiers the reference actually observed persistently**, no more than one nuisance notification per two hours on agreed controls, and a four-hour intended-use session. Those are targets to challenge, not marketing figures. Publish the unconditional fraction of participant passes that were visible alongside conditional recall, so invisible phones cannot disappear from the denominator. Report route-hours and uncertainty; a few clean demonstrations cannot establish a low false-alert rate.

For each missed case, classify the cause: no observed emission, channel miss/unknown coverage, adapter loss, address change, GPS rejection, threshold or software defect. This is the most useful research output for deciding what to improve next.

## Simple architecture and maintenance

Keep five boundaries: capture adapters → immutable observations → bounded store → pure recurrence/encounter rules → CLI/browser/Pager views. GPS is observer metadata with provenance, not a global “last coordinate.” UI code must not duplicate detection logic. Experimental aliases are separate removable edges between observations, never replacements for original addresses.

Before adding live sensors, extend the event contract deliberately for capture-source identity, channel/band and coverage intervals, GPS source/receipt time and error convention. Version the schema and migration once; avoid adding unversioned optional fields that change the serialized body of existing source events. This milestone leaves the stored observation schema unchanged.

Keep standard-library dependencies until measured needs justify another package. Avoid separate daemon wrappers that independently poll and score the same data. Preserve one test suite, a supported-version matrix and small replay fixtures. Archive the legacy application at an announced release boundary after migration, rather than carrying two maintained products indefinitely.

## Selling a configured unit without manufacturing hardware

This is plausible as a software/provisioning business using an OEM Pager and GPS module. Manufacturing a custom enclosure or radio board is not required for the first bundle. Three models are possible:

| Model | Practical responsibility | Recommendation |
| --- | --- | --- |
| Customer buys the hardware; CYT provides installer and support | Software compatibility, documentation and updates | Start here after Pi/Pager validation; lowest inventory exposure |
| Reseller/fulfillment partner loads CYT and ships a tested bundle | Agree provisioning, version pinning, acceptance checks, returns and support split | Best route to “preconfigured” without assembling each unit yourself |
| CYT buys, configures and resells units | Stock, provisioning labor, warranty/returns handling and shipping | Defer until demand and unit economics are measured |

Hak5 publicly offers an authorized-reseller contact route, but this review found no commitment that it or another seller will preload CYT, dropship it, grant a particular margin, or support modifications. Those need a written agreement; no partner has been contacted. The official shop advertises Pager from $300, but GPS/bundle variants and stock change. A fresh reliable variant-level quote was not obtainable in this review, so do not turn the older price snapshot into a current offer. [Hak5 reseller program](https://hak5.org/pages/authorized-resellers), [official shop](https://shop.hak5.org/).

Calculate unit economics from an actual quote: hardware + GPS + provisioning/test labor + freight/payment costs + expected returns + a support reserve. Price software/support separately enough that a firmware update or a failed unit does not consume the entire margin. Confirm software redistribution and branding terms for every bundled component and the partner's warranty arrangements before advertising affiliation or taking preorders.

The initial paid audience should be practitioners who understand radio evidence and its limits. Do not launch as a guaranteed personal-safety device. Publish supported radios/states, limitations, local-data behavior and measured endurance with the product.

## A credible public launch

Lead with the changed technical problem: modern phone privacy broke the old remembered-SSID assumption. Show both a successful persistent-hotspot route and an ordinary phone that cannot be followed consistently. Include a companion and fixed-AP counterexample. Publish normalized, consented fixtures, versioned rules and missed cases so others can repeat the results.

That is a defensible conference/demo story: what can still be measured, which proposed shortcuts fail, and a small tool that presents the evidence honestly. A compelling Pager form factor can make that work accessible once the Pi results justify it.
