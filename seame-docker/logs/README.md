---
title: Simulator Measurements
---
# Logs: test runs and measurements

Every test run and every measurement gets its own dated folder, so results can be compared over time (getting better or worse) and traced back to the exact code that produced them. Nothing here is written by hand except notes.

```
logs/
├── tests/
│   ├── history.csv                          one line per run: the trend at a glance
│   └── 2026-11-04_121721_c240f26/           <date>_<time>_<commit>, one per run
│       ├── meta.json                        when, commit, branch, uncommitted files
│       ├── report.md                        the readable report
│       ├── results.json                     every test case, with any failure message
│       └── console.log.gz                   the full output (zcat console.log.gz | less)
└── measurements/
    └── <name>/                              e.g. wifi_rtt, cmd_rate
        ├── history.csv                      one line per measurement
        └── <date>_<time>_<commit>/
            ├── meta.json
            └── values.json                  (plus whatever the measuring tool saves)
```

**`-dirty` in a folder name** means the run included uncommitted changes under `ros2_ws/`, so the commit alone doesn't say what ran; `meta.json` and the report list the files. Uncommitted docs are listed but don't make a run dirty.

## Tests

On the host, in `seame-docker/`, with the dev container running:

```bash
./scripts/run_tests.sh
```

A clean build and `colcon test` inside the container, with the same commands as CI, built under `/tmp` so the workspace's `build/` and `install/` are untouched. About 1.5 minutes. It prints the verdict and the report's path, and exits non-zero if the build failed or any test failed.

The report compares with the previous run: new tests, tests gone, and any test whose result changed. `history.csv` columns: run, date, commit, dirty, verdict, cases, passed, skipped, failed, behaviour, lint, build_s, test_s.

Commit the run folder together with the code it tested, or right after, so the history stays in the repo. A run is about 60 KB.

## Measurements

Anything measured over time: Wi-Fi round-trip time and drops (STK-5), command rates (ROS-7.1), and later anything else worth tracking.

**Wi-Fi round trip (`wifi_rtt`)**, with the laptop on the drone's network:

```bash
python3 scripts/measure_wifi_rtt.py --note "bench, AP mode, radio on" -n 1000 --interval 0.05
```

It runs [`telemetry/latency_test.py`](../../telemetry/latency_test.py) (any of its flags pass through) and keeps its per-sample CSV as `samples.csv`. `values.json` and `history.csv` hold: `host`, `duration_s`, `rate_hz` (the real request rate; `--interval` is the pause between samples, so it's lower than 1/interval), `sent`, `answered`, `lost`, `lost_pct`, `late`, `corrupted`, `min_ms`, `median_ms`, `p90_ms`, `p99_ms`, `max_ms`, `jitter_ms`, plus the flags used and the note. Ctrl-C stops early and still records the run; a run that never connected records nothing.

**From a measuring script** (Python), the way `run_tests.sh` does it:

```python
import sys; sys.path.insert(0, 'scripts')
from logbook import new_run, append_history, write_json

run = new_run('measurements', 'cmd_rate', {'note': 'sim demo, /cmd/mission'})
# ... measure, save raw data into run/ ...
write_json(f'{run}/values.json', {'hz': 19.8, 'jitter_ms': 4.1})
append_history(run, {'hz': 19.8, 'jitter_ms': 4.1, 'note': 'sim demo, /cmd/mission'})
```

**Measured by hand or with another tool:**

```bash
python3 scripts/logbook.py measure cmd_rate hz=19.8 jitter_ms=4.1 --note "sim demo, /cmd/mission"
```

Use one name per kind of measurement, and keep the same keys between runs so `history.csv` stays comparable; a new key just adds a column. Always say the conditions in `--note` (where, what was running, anything unusual): a number without its setup can't be compared.

# Tags

#resources 