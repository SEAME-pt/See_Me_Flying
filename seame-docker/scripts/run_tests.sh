#!/bin/bash
# ---------------------------------------------------------------------------- #
#     Run every ROS test, keep the results in logs/tests/<date>_<commit>/       #
# ---------------------------------------------------------------------------- #
# Clean build and colcon test inside the dev container, with the same commands
# as CI (.github/workflows/ci.yml). Builds into /tmp in the container, so the
# workspace's own build/ and install/ are never touched. Then writes report.md,
# results.json and a line in logs/tests/history.csv (scripts/test_report.py).
#
# Usage, on the host in seame-docker/:   ./scripts/run_tests.sh
# Exit code 0 only if the build worked and no test failed.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -z "$(docker compose ps -q --status running dev)" ]; then
    echo "❌ The dev container isn't running. Start it: docker compose up -d"
    exit 2
fi

RUN=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from logbook import new_run; print(new_run('tests'))")
echo "📁 ${RUN#"$PROJECT_DIR"/}"

# Inside the container: clean build + test, everything into /tmp/seame_tests.
docker compose exec -T dev bash -s <<'EOF'
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
OUT=/tmp/seame_tests
rm -rf "$OUT" && mkdir -p "$OUT"
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
} > "$OUT/console.log" 2>&1
grep '^### .*exit=' "$OUT/console.log"
EOF

# Bring back the console log and every result file (pytest, xUnit, CTest).
docker compose exec -T dev bash -c 'cd /tmp/seame_tests && tar cf - console.log \
    $(find build \( -path "*/test_results/*" -name "*.xml" \) -o -name pytest.xml \
      -o \( -path "*/Testing/*" -name Test.xml \) | grep -v /CMakeFiles/)' \
    | tar xf - -C "$RUN"

python3 scripts/test_report.py "$RUN"
