---
title: Test and Measurement Logs
---
# Logs: test runs and measurements

Every test run and every measurement gets its own dated folder, so results can be compared over time (getting better or worse) and traced back to the exact code that produced them. Nothing here is written by hand except notes.

```
project/logs/
├── tests/                                   make test
│   ├── history.csv                          one line per run: the trend at a glance
│   └── 2026-11-04_eba9334/                  <date>_<commit>, one per run
│       ├── meta.json                        when, commit, branch, uncommitted files
│       ├── report.md                        the readable report
│       ├── results.json                     every test case, with any failure message
│       └── console.log.gz                   the full output (zcat console.log.gz | less)
├── sim_flight/                              make sim-test
│   ├── history.csv
│   └── <date>_<commit>/                     meta.json, result.json, flight.log, flight.xml, build.log
└── measurements/
    └── <n>/                                 e.g. wifi_rtt, inav_link, inav_rc_override, motor_music
        ├── history.csv                      one line per measurement
        └── <date>_<commit>/
            ├── meta.json
            └── values.json                  (plus whatever the measuring tool saves, and notes.md)
```

The tools that write here live in `project/scripts/`: `logbook.py` (run folders and history), `run_tests.sh`, `sim_flight_test.sh`, `measure_wifi_rtt.py` and the bench scripts.

**`-dirty` in a folder name** means the run included uncommitted changes under `project/ros2/src/` or `project/telemetry/`, so the commit alone doesn't say what ran; `meta.json` and the report list the files. Uncommitted docs are listed but don't make a run dirty.

**`-2`, `-3` at the end** means the same commit was run again that day. The exact time of every run is in `meta.json` and in the `date` column of `history.csv`.

## Tests

From the repo root, on the host:

```bash
make test
```

A clean build and `colcon test` inside the container, with the same commands as CI, built under `/tmp` so the workspace's `build/` and `install/` are untouched, then the telemetry tests (`project/telemetry/tests/`). About 2 minutes. It prints the verdict and the report's path, and exits non-zero if the build failed or any test failed. What each test checks: [ROS 2 stack](../ros2/README.md#tests) and [CI_Tests](../../docs/CI_Tests.md).

The report compares with the previous run: new tests, tests gone, and any test whose result changed. `history.csv` columns: run, date, commit, dirty, verdict, cases, passed, skipped, failed, behaviour, lint, build_s, test_s.

Commit the run folder together with the code it tested, or right after, so the history stays in the repo. A run is about 60 KB. (When Claude Code commits code, a hook in `.claude/` asks for a test run first.)

## Gazebo flight

```bash
make sim-test
```

The headless Gazebo flight test, the same as the nightly CI job, in a throwaway container: takeoff, hover, a square, the speed limits, the mission killed mid-flight, landing. About 2 minutes, and your own sim can stay open. The run folder gets `result.json` (verdict and steps), `flight.log`, `flight.xml` (xUnit) and `build.log`; the flight's rosbag (`flight_bag/`) and every node's log (`ros_log/`) stay on your disk only.

## Measurements

Anything measured over time: Wi-Fi round-trip time and drops (STK-5), command rates (ROS-7.1), the `inav` backend on the real drone (`inav_link`: topic rates, reconnect time, plus the bench notes and a bag), ROS sticks through MSP RC OVERRIDE (`inav_rc_override`, `make bench-rc` and `make bench-armed`), the motors playing a song (`motor_music`, `make motor-music`), and later anything else worth tracking.

**Wi-Fi round trip (`wifi_rtt`)**, with the laptop on the drone's network:

```bash
make wifi-rtt NOTE="bench, AP mode, radio on" ARGS="--port 23 -n 1000 --interval 0.05"
```

It runs [`project/telemetry/latency_test.py`](../telemetry/latency_test.py) (any of its flags pass through in `ARGS`; `--port 23` is needed for esp-link, since the script still defaults to 5760) and keeps its per-sample CSV as `samples.csv`. `values.json` and `history.csv` hold: `host`, `duration_s`, `rate_hz` (the real request rate; `--interval` is the pause between samples, so it's lower than 1/interval), `sent`, `answered`, `lost`, `lost_pct`, `late`, `corrupted`, `min_ms`, `median_ms`, `p90_ms`, `p99_ms`, `max_ms`, `jitter_ms`, plus the flags used and the note. Ctrl-C stops early and still records the run; a run that never connected records nothing. Earlier results: [Wi-Fi latency tests](../../docs/Telemetry_test.md).

**From a measuring script** (Python, run from the repo root), the way `run_tests.sh` does it:

```python
import sys; sys.path.insert(0, 'project/scripts')
from logbook import new_run, append_history, write_json

run = new_run('measurements', 'cmd_rate', {'note': 'sim demo, /cmd/mission'})
# ... measure, save raw data into run/ ...
write_json(f'{run}/values.json', {'hz': 19.8, 'jitter_ms': 4.1})
append_history(run, {'hz': 19.8, 'jitter_ms': 4.1, 'note': 'sim demo, /cmd/mission'})
```

**Measured by hand or with another tool:**

```bash
python3 project/scripts/logbook.py measure cmd_rate hz=19.8 jitter_ms=4.1 --note "sim demo, /cmd/mission"
```

Use one name per kind of measurement, and keep the same keys between runs so `history.csv` stays comparable; a new key just adds a column. Always say the conditions in `--note` (where, what was running, anything unusual): a number without its setup can't be compared.

# Tags

#tests
