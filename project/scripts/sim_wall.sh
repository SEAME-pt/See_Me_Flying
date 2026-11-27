#!/bin/bash
# ---------------------------------------------------------------------------- #
#      Gazebo: fly forward until something gets in the way (empty wall)        #
# ---------------------------------------------------------------------------- #
# No radio and no keyboard: the drone takes off by itself, flies at the wall and
# hovers in front of it. Extra launch arguments: make sim-wall ARGS="speed:=0.3"

set -e

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPTS/../.." && pwd)"   # compose.yaml lives here
source "$SCRIPTS/open_tabs.sh"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_WALL="cd '$REPO_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup wall_mission.launch.py $*'"

# Closes older sim processes, avoiding duplicates
bash "$SCRIPTS/stop_sim.sh"

open_tabs "Gazebo Wall Mission" "$CMD_WALL"
