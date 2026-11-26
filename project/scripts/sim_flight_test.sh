#!/bin/bash
# ---------------------------------------------------------------------------- #
#     Gazebo flight test, headless, in a fresh dev container (what nightly runs) #
# ---------------------------------------------------------------------------- #
# Run by `make sim-test`. Starts a throwaway container from the dev image, with no
# display and no GPU like GitHub's machines, copies project/ros2/src into it,
# builds, and flies drone_bringup/test/test_sim_flight.py (about 2 min). Your dev
# container and its build/ are not touched, so it also runs while your own sim is open.
# 
# ! SUITE=sensors flies drone_bringup/test/test_sim_sensors.py instead (the simulated
# sensors and the estimator against ground truth, about 2.5 min); its results go to
# project/logs/sim_sensors/.
#
# Results, in project/logs/sim_flight/<date>_<commit>/ (or the folder given as the
# first argument, as the nightly workflow does: then no history line is written):
#   meta.json    when, commit, uncommitted files    result.json  verdict and steps
#   flight.log   the test's output, with what each step measured
#   flight.xml   xUnit report         build.log    colcon build
#   flight_bag/  rosbag: ros2 bag play flight_bag   ros_log/  every node's log
#   (flight_bag/ and ros_log/ stay on your disk only: .gitignore keeps them out of git)
# and a line in project/logs/sim_flight/history.csv.
# Exit code 0 only if every flight step passed.

set -euo pipefail

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPTS/.." && pwd)"
IMAGE="${SIM_IMAGE:-seame/ros2-dev:jazzy}"

# Which test: SUITE=flight (the default, what nightly runs) or SUITE=sensors.
SUITE="${SUITE:-flight}"
case "$SUITE" in
    flight)  TEST=test_sim_flight.py;  KIND=sim_flight;  DOMAIN=196; PART=flight_test
             SHOW='on the ground:|takeoff: true|hover 10 s|side [0-9]:|square closes|2 m/s asked|landed:|mission killed' ;;
    sensors) TEST=test_sim_sensors.py; KIND=sim_sensors; DOMAIN=197; PART=sensor_test
             SHOW='carpet lane|hover 10 s|4 m pass|creep [0-9]' ;;
    *) echo "Error: SUITE must be flight or sensors, not '$SUITE'"; exit 2 ;;
esac

if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
    echo "Error: No $IMAGE image. Build it first: make build"
    exit 2
fi

RUN=""
if [ $# -ge 1 ]; then
    OUT="$1"
else
    RUN=$(python3 -c "import sys; sys.path.insert(0, '$SCRIPTS'); from logbook import new_run; print(new_run('$KIND'))")
    OUT="$RUN"
fi
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
chmod a+rwx "$OUT"   # the container's user (dev) writes here, whatever the host user is
echo "Results in $OUT"

# Inside the container. Passed with bash -c, not on stdin: rosbag reads the keyboard.
INSIDE=$(cat <<'EOF'
set -o pipefail          # not -u: ROS's setup.bash reads unset variables
source /opt/ros/jazzy/setup.bash
mkdir -p /tmp/ws && cp -r /src /tmp/ws/src && cd /tmp/ws
echo "### build"
if ! colcon build --packages-up-to drone_bringup > /results/build.log 2>&1; then
    tail -40 /results/build.log
    exit 1
fi
source install/setup.bash
# Own domain, localhost only, own Gazebo partition: nothing else can join this sim.
export ROS_DOMAIN_ID=$DOMAIN ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=$PART
ros2 bag record -o /results/flight_bag /sim/ground_truth /fc/status /fc/range /fc/odom \
    /cmd/mission /cmd/manual /fc/setpoint_velocity /X3/gazebo/command/twist \
    /safety/active_source /fc/optical_flow /fc/attitude < /dev/null > /results/bag.log 2>&1 &
bag=$!
echo "### $TEST"
launch_test src/drone_bringup/test/$TEST --junit-xml /results/flight.xml \
    < /dev/null > /results/flight.log 2>&1
status=$?
# TERM, not INT: a job started with & in a script ignores SIGINT, and the recorder
# would never stop. It closes the bag cleanly on SIGTERM.
kill -TERM $bag
wait $bag
cp -r ~/.ros/log /results/ros_log 2>/dev/null
# What each step measured, then the verdict.
grep -oE "($SHOW)[^[]*" /results/flight.log
grep -E "^(OK|FAILED)|^(FAIL|ERROR):|^AssertionError" /results/flight.log
exit $status
EOF
)

start=$(date +%s)
set +e
docker run --rm -e TEST="$TEST" -e DOMAIN="$DOMAIN" -e PART="$PART" -e SHOW="$SHOW" \
    -v "$PROJECT_DIR/ros2/src:/src:ro" -v "$OUT:/results" "$IMAGE" bash -c "$INSIDE"
status=$?
set -e

# Logbook run: result.json and a history line (steps passed/failed from the xUnit report).
if [ -n "$RUN" ]; then
    python3 - "$SCRIPTS" "$RUN" "$status" "$(( $(date +%s) - start ))" <<'PY'
import os, sys
import xml.etree.ElementTree as ET
sys.path.insert(0, sys.argv[1])
from logbook import append_history, write_json
run, status, seconds = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
steps = []
xml = os.path.join(run, 'flight.xml')
if os.path.exists(xml):
    for tc in ET.parse(xml).getroot().iter('testcase'):
        bad = [t for t in ('failure', 'error', 'skipped') if tc.find(t) is not None]
        steps.append({'name': tc.get('name'), 'status': bad[0] if bad else 'passed',
                      'time': float(tc.get('time') or 0)})
verdict = 'PASSED' if status == 0 else 'FAILED'
count = {s: sum(x['status'] == s for x in steps) for s in ('passed', 'skipped', 'failure', 'error')}
write_json(os.path.join(run, 'result.json'),
           {'verdict': verdict, 'exit': status, 'seconds': seconds, 'counts': count, 'steps': steps})
append_history(run, {'verdict': verdict, 'steps': len(steps), 'passed': count['passed'],
                     'failed': count['failure'] + count['error'], 'skipped': count['skipped'],
                     'seconds': seconds})
print(f'{verdict}: {count["passed"]}/{len(steps)} flight steps passed, {seconds} s')
PY
fi
exit $status
