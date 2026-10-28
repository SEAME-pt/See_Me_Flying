#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (joystick)                #
# ---------------------------------------------------------------------------- #

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/scripts/open_tabs.sh"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_GAZEBO_JOY="cd '$PROJECT_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=joy'"
CMD_RADIO_TELEOP="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_py radio_teleop'"

open_tabs "Gazebo Joy Sim" "$CMD_GAZEBO_JOY" \
          "Radio Teleop Node" "$CMD_RADIO_TELEOP"
