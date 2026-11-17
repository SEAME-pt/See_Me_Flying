#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (joystick)                #
# ---------------------------------------------------------------------------- #

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# Gazebo window view: free (default), follow or fpv; start.sh asks for it.
CAMERA="${1:-free}"
source "$PROJECT_DIR/scripts/open_tabs.sh"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

# The launch starts joy_node and radio_teleop itself (source:=joy is gone).
# SA arms (throttle centred), the takeover switch hands over the sticks.
CMD_GAZEBO_JOY="cd '$PROJECT_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none world:=room_world.sdf camera:=$CAMERA'"

# Closes older sim processes, avoiding duplicates
bash "$PROJECT_DIR/scripts/stop_sim.sh"

open_tabs "Gazebo Joy Sim" "$CMD_GAZEBO_JOY"
