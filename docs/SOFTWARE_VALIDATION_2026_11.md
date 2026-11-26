# Software validation — November 26, 2026

These are synthetic software results on a Windows 11 host with Python 3.13.11. No Raspberry Pi, Pager, GPS receiver, phone or RF environment was measured. The observations are artificial; none of the results establishes detection accuracy, battery life, actual process RAM on Pager, or a safe user alert threshold.

## Functional checks

The current suite has 70 tests. Local checks passed after the GPS join, explicit threshold controls and streamed-report changes. An isolated `0.2.0a2` package installation succeeded, and its installed GPS module and command help were checked outside the source checkout. All four Windows/Linux and Python 3.10/3.13 jobs passed for runtime commit `1fdcb2c`, including packaging and installed-command checks ([CI run](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/actions/runs/45866424347)). Revision-specific checks continue in [GitHub Actions](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/actions/workflows/core-tests.yml).

Eleven reproducible route scenarios cover useful persistence and its counterexamples:

```sh
python -B research/evaluate_route_cases.py
```

All policy checks pass. In particular, the persistent-hotspot, companion and fixed-AP-over-a-route inputs produce identical reports. This confirms a limitation of the observations, not successful discrimination between those scenarios. Address rotation splits records; a silent participant produces no observation. The tests must not be presented as a percentage of followers detected.

## Report memory experiment

`research/benchmark_core.py` creates a temporary store with fixed synthetic timestamps, six observer positions and the requested number of distinct identifiers. It measures three ordinary reports, then performs a separate traced-allocation pass. Data are not collected from radios.

The previous report method retained a full list of JSON rows alongside the decoded observations. Streaming the SQLite cursor removes that duplicate window without changing recurrence semantics. The baseline method matches `main` at `d73dc6d`; the candidate uses the streamed query in this change.

| Observations / identifiers | Before: peak traced Python allocations | After: peak traced Python allocations | Before / after report median |
| --- | --- | --- | --- |
| 10,000 / 100 | 14.1 MB | 8.9 MB | 0.144 / 0.151 s |
| 100,000 / 1,000 | 143.7 MB | 91.3 MB | 3.55 / 3.84 s |
| 100,000 / 100,000 | 258.9 MB | 206.6 MB | 4.05 / 4.36 s |

MB means 1,000,000 bytes. These are Python allocation peaks, **not whole-process RSS**. SQLite, interpreter and native allocations are not fully represented. The host was also running an ingestion soak, so these timing differences are not an isolated speed comparison. The goal was to expose memory cost and verify a reduction; no speed improvement is claimed.

The dense-identifier case remains far too large to assume safe on a 256 MB Pager that must also run vendor services. Start Pager evaluation with a smaller event cap, measure actual process/system memory and backlog, and reduce the analysis window or change the aggregation design if needed. A cap on returned UI rows does not cap the analysis allocation.

There is a competing retention constraint. The 5,000-row soak buffer at about 100 accepted rows/second retains only about 50 seconds, so the default 120-second recurrence span cannot qualify even though ingestion is healthy. The soak is a durability test, not evidence that its small buffer is a useful detection configuration. A future compact evidence layer must preserve longer encounter history without retaining every repetitive frame in analysis memory; its results need comparison with unpruned replay. Reducing the row cap without this check can make the application less useful.

Reproduce on the intended device, storing temporary files on an appropriate local data filesystem:

```sh
python -B research/benchmark_core.py --events 10000 --identifiers 100
python -B research/benchmark_core.py --events 100000 --identifiers 1000
python -B research/benchmark_core.py --events 100000 --identifiers 100000
```

The last two commands are desktop/Pi stress cases, not recommended Pager defaults. Set the OS temporary directory to the intended data partition before running them. Test both many events per identifier and many distinct identifiers; they stress different parts of the report.

## Sustained ingestion protocol

The reusable synthetic soak writes 100 Wi-Fi packet rows about once a second, using 100 advertised addresses, including wildcard probes, named probes and beacons. It rotates the input after 120 iterations, checks duplicate ingestion every 30, restarts the store connection every 300, and reports the current 120-second window. Retention is 90 seconds plus a 5,000-observation cap. Original synthetic capture files remain in the output directory.

```sh
python -B research/soak_runtime.py --seconds 3600 --output /path/to/new-synthetic-run
```

The output directory must not exist. `progress.json` is an intermediate sample; only a successful exit and `result.json` with `result: passed` mean the run completed. Assertions check that every written packet was inserted once and the retained count stays within the cap. The run exercises library ingestion/report/storage, not the CLI supervisor or a real capture process. Restart means reopening a database connection, not an operating-system crash.

Both sustained runs completed successfully:

| Runtime | Duration | Written / inserted | Capture files | Store reopenings | Duplicate checks | Retained |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (`d73dc6d`) | 3600.7 s | 359,900 / 359,900 | 30 | 11 | 120 | 5,000 |
| streamed_report (`1fdcb2c`) | 1200.5 s | 120,000 / 120,000 | 10 | 3 | 40 | 5,000 |

The [machine-readable results](../research/soak-results-2026-11-26.json) retain counts and timing/allocation summaries. The baseline process loaded the previously shipped runtime; the second process exercised the streamed report. A source edit cannot retroactively change modules in a running process.

Producer and consumer share this synthetic loop, so it is not an independent constant-rate capture/backlog test. The run lengths and source counts differ; their timing summaries are not a controlled before/after comparison. Neither run exercised live GPS, real RF capture, an OS crash, physical power loss or battery endurance.
