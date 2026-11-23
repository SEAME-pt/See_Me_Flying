#!/bin/bash
# ---------------------------------------------------------------------------- #
#   Run every test, keep the results in project/logs/tests/<date>_<commit>/    #
# ---------------------------------------------------------------------------- #
# Run by `make test`. In the dev container:
#   1. clean colcon build and colcon test of project/ros2/src, the same commands
#      as CI (.github/workflows/ci.yml), built under /tmp so the workspace's own
#      build/ and install/ are never touched;
#   2. the telemetry tests (project/telemetry/tests, plain pytest, as CI does).
# Then test_report.py writes into the run folder:
#   meta.json       when, commit, branch, uncommitted files
#   report.md       the readable report, compared with the previous run
#   results.json    every test case, with any failure message
#   console.log.gz  the full output (zcat console.log.gz | less)
# and adds a line to project/logs/tests/history.csv.
# Exit code 0 only if the build worked and no test failed.

set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPTS/../.." && pwd)"
cd "$REPO_DIR"   # docker compose finds compose.yaml and .env here

if [ -z "$(docker compose ps -q --status running dev)" ]; then
    echo "Error: The dev container isn't running. Start it: make up"
    exit 2
fi

RUN=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPTS'); from logbook import new_run; print(new_run('tests'))")
echo "Results in ${RUN#"$REPO_DIR"/}"

# Inside the container: clean build + test, everything into /tmp/seame_tests.
docker compose exec -T dev bash -s <<'EOF'
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
OUT=/tmp/seame_tests
rm -rf "$OUT" && mkdir -p "$OUT/build/telemetry"
B="--build-base $OUT/build --install-base $OUT/install"
{
  echo "### ROS_DISTRO=$ROS_DISTRO  $(lsb_release -ds 2>/dev/null)  python $(python3 -c 'import platform;print(platform.python_version())')"
  echo "### colcon build"
  start=$(date +%s)
  colcon --log-base "$OUT/log" build $B --event-handlers console_direct+ 2>&1
  echo "### build exit=$? seconds=$(( $(date +%s) - start ))"
  source "$OUT/install/setup.bash"
  echo "### colcon test"
  start=$(date +%s)
  colcon --log-base "$OUT/log" test $B --event-handlers console_direct+ 2>&1
  echo "### test exit=$? seconds=$(( $(date +%s) - start ))"
  echo "### colcon test-result --verbose"
  colcon test-result --test-result-base "$OUT/build" --verbose 2>&1
  echo "### test-result exit=$?"
  echo "### telemetry pytest"
  start=$(date +%s)
  # No cache or .pyc files in the mounted project/telemetry.
  PYTHONDONTWRITEBYTECODE=1 python3 -m pytest ~/project/telemetry -v -p no:cacheprovider \
      --junitxml="$OUT/build/telemetry/pytest.xml" 2>&1
  echo "### telemetry exit=$? seconds=$(( $(date +%s) - start ))"
} > "$OUT/console.log" 2>&1
grep '^### .*exit=' "$OUT/console.log"
EOF

# Bring back the console log and every result file (pytest, xUnit, CTest).
docker compose exec -T dev bash -c 'cd /tmp/seame_tests && tar cf - console.log \
    $(find build \( -path "*/test_results/*" -name "*.xml" \) -o -name pytest.xml \
      -o \( -path "*/Testing/*" -name Test.xml \) | grep -v /CMakeFiles/)' \
    | tar xf - -C "$RUN"

python3 "$SCRIPTS/test_report.py" "$RUN"
