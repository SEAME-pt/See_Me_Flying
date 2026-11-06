---
name: run-tests
description: Run the See_Me_Flying ROS test suite the standard way (scripts/run_tests.sh), record it in seame-docker/logs/tests/, and summarize what changed since the last run. Use when asked to run the tests or "the tester", before a commit or pull request, or to check whether a change broke something.
---

# Run the tests and record them

Always use the tester, never a bare `colcon test`, when the result should be kept: it does a clean build with CI's commands and writes a dated run folder with the commit it ran on.

## Steps

1. **Container running?** In `seame-docker/`: `docker compose ps --status running dev`. If it isn't, ask the user before starting it (`docker compose up -d` can recreate it with a changed `compose.yaml`; `docker start seame-dev` starts the existing one as it is).
2. **Run it** from `seame-docker/`: `./scripts/run_tests.sh`. About 1.5–2 minutes; run it in the background and wait for it to finish. The last lines give the verdict and the report path. Exit code 0 = build worked and nothing failed.
3. **Read** `logs/tests/<run>/report.md`, not the console. Report to the user, in this order:
   - the verdict and the counts (behaviour tests and lint separately; skipped and why if it changed);
   - **every failure**, with its message; for the detail, `zcat logs/tests/<run>/console.log.gz | grep -n '<test name>' -A40`;
   - the "Compared with the previous run" section: new tests, tests gone, results that changed. A test that went from pass to fail is the headline;
   - new warnings, if any;
   - if the folder name ends in `-dirty`: say that uncommitted code changes were part of the run.
4. **Don't edit** anything in a run folder or `history.csv` by hand; a wrong run is deleted (folder and its `history.csv` line), not corrected.
5. **Offer to commit** the run folder and `history.csv`, together with the code they tested or right after it.

## Notes

- The run doesn't touch the workspace's `build/` or `install/` (it builds under `/tmp` in the container), so it's safe while the user has a sim running, apart from the CPU load.
- `fc_bridge` launch tests run on `ROS_DOMAIN_ID=199`, localhost only; a running sim on another domain doesn't interfere.
- colcon's own "N tests" counts CTest wrappers too; the report's test case count is the real one.
- Measurements go in `logs/measurements/<name>/` through `scripts/logbook.py` (see `seame-docker/logs/README.md`), not through this skill.
