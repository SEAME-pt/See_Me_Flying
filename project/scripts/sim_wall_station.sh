#!/bin/bash
# ---------------------------------------------------------------------------- #
#     Ground station half of the wall mission (make sim-wall-station)          #
# ---------------------------------------------------------------------------- #
# Run on the ground station (the Raspberry Pi 5, over SSH) while a laptop on the
# same network runs make sim-wall-drone: the laptop plays the drone (Gazebo), and
# this runs the mission, sweep_view and forward_flight, as on the real drone.
# Both need ROS_DOMAIN_ID 6 (the dev container sets it). In this terminal, no
# tabs: the Pi has no desktop. sweep_view's window opens only with a screen.
# Extra launch arguments: make sim-wall-station ARGS="speed:=0.2"

set -e

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPTS/../.." && pwd)"   # compose.yaml lives here

cd "$REPO_DIR"
# Stops an earlier station run only: not stop_sim.sh, which would also end a
# drone half running in this same container (both halves on one laptop).
docker compose exec -T dev bash -c '
  pkill -INT -f "[w]all_mission.launch.py part:=station" && sleep 2
  true'
exec docker compose exec -e DISPLAY="${DISPLAY:-}" dev bash -c "cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup wall_mission.launch.py part:=station $*"
