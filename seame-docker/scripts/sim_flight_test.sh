#!/bin/bash
# ---------------------------------------------------------------------------- #
#     Gazebo flight test, headless, in a fresh dev container (what nightly runs) #
# ---------------------------------------------------------------------------- #
# Starts a throwaway container from the dev image, with no display and no GPU
# like GitHub's machines, copies ros2_ws/src into it, builds, and flies
# drone_bringup/test/test_sim_flight.py (about 2 min). Your dev container and
# its build/ are not touched, so it also runs while your own sim is open.
#
# Results go to the folder given as the first argument (default:
# ros2_ws/log/sim_flight/<date>/, ignored by git):
#   flight.log   the test's output, with what each step measured
#   flight.xml   xUnit report         flight_bag/  rosbag: ros2 bag play flight_bag
#   build.log    colcon build         ros_log/     every node's log
#
# Usage, on the host in seame-docker/:   ./scripts/sim_flight_test.sh [results_dir]
# Exit code 0 only if every flight step passed.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${SIM_IMAGE:-seame/ros2-dev:jazzy}"
OUT="${1:-$PROJECT_DIR/ros2_ws/log/sim_flight/$(date +%Y-%m-%d_%H-%M-%S)}"
mkdir -p "$OUT"
OUT="$(cd "$OUT" && pwd)"
chmod a+rwx "$OUT"   # the container's user (dev) writes here, whatever the host user is

if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
    echo "❌ No $IMAGE image. Build it first: docker compose build"
    exit 2
fi
echo "📁 $OUT"

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
export ROS_DOMAIN_ID=196 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=flight_test
ros2 bag record -o /results/flight_bag /sim/ground_truth /fc/status /fc/range /fc/odom \
    /cmd/mission /cmd/manual /fc/setpoint_velocity /X3/gazebo/command/twist \
    /safety/active_source < /dev/null > /results/bag.log 2>&1 &
bag=$!
echo "### flight test (about 2 min)"
launch_test src/drone_bringup/test/test_sim_flight.py --junit-xml /results/flight.xml \
    < /dev/null > /results/flight.log 2>&1
status=$?
# TERM, not INT: a job started with & in a script ignores SIGINT, and the recorder
# would never stop. It closes the bag cleanly on SIGTERM.
kill -TERM $bag
wait $bag
cp -r ~/.ros/log /results/ros_log 2>/dev/null
# What each step measured, then the verdict.
grep -oE "(on the ground:|takeoff: true|hover 10 s|side [0-9]:|square closes|2 m/s asked|landed:|mission killed)[^[]*" /results/flight.log
grep -E "^(OK|FAILED)|^(FAIL|ERROR):|^AssertionError" /results/flight.log
exit $status
EOF
)

docker run --rm -v "$PROJECT_DIR/ros2_ws/src:/src:ro" -v "$OUT:/results" "$IMAGE" bash -c "$INSIDE"
