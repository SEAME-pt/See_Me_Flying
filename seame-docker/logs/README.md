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

**From a measuring script** (Python), the way `run_tests.sh` does it:

```python
import sys; sys.path.insert(0, 'scripts')
from logbook import new_run, append_history, write_json

run = new_run('measurements', 'wifi_rtt', {'note': 'bench, radio on'})
# ... measure, save raw data into run/ ...
write_json(f'{run}/values.json', {'mean_ms': 12.4, 'p95_ms': 30.1, 'drops': 0})
append_history(run, {'mean_ms': 12.4, 'p95_ms': 30.1, 'drops': 0, 'note': 'bench, radio on'})
```

**Measured by hand or with another tool:**

```bash
python3 scripts/logbook.py measure wifi_rtt mean_ms=12.4 p95_ms=30.1 drops=0 --note "bench, radio on"
```

Use one name per kind of measurement, and keep the same keys between runs so `history.csv` stays comparable; a new key just adds a column. Always say the conditions in `--note` (where, what was running, anything unusual): a number without its setup can't be compared.
