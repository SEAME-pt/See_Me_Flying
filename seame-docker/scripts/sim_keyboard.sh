#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (keyboard)                #
# ---------------------------------------------------------------------------- #

set -e

# radio:=false: no Pocket, so the drone starts armed (only the radio arms otherwise).
# The keyboard publishes on /cmd/manual; safety_manager forwards it to fc_bridge.

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/scripts/open_tabs.sh"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_GAZEBO="cd '$PROJECT_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none radio:=false world:=room_world.sdf'"
CMD_KEYBOARD="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/cmd/manual'"

# Closes older sim processes, avoiding duplicates
bash "$PROJECT_DIR/scripts/stop_sim.sh"

open_tabs "Gazebo Sim" "$CMD_GAZEBO" \
          "Keyboard Teleop" "$CMD_KEYBOARD"





