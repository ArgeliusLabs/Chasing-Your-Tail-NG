# Software validation — November 26, 2026

These are synthetic software results on a Windows 11 host with Python 3.13.11. No Raspberry Pi, Pager, GPS receiver, phone or RF environment was measured. The observations are artificial; none of the results establishes detection accuracy, battery life, actual process RAM on Pager, or a safe user alert threshold.

## Functional checks

The current suite has 70 tests. Local checks passed after the GPS join, explicit threshold controls and streamed-report changes. An isolated `0.2.0a2` package installation succeeded, and its installed GPS module and command help were checked outside the source checkout. Revision-specific Windows/Linux checks run in [GitHub Actions](https://github.com/ArgeliusLabs/Chasing-Your-Tail-NG/actions/workflows/core-tests.yml).

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

The one-hour baseline run and a 20-minute streamed-query run are being recorded separately. Their final results will be added after completion. This distinction matters: a source edit cannot retroactively change modules already loaded into a running test process.
