#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (keyboard)                #
# ---------------------------------------------------------------------------- #

set -e

# radio:=false: no Pocket, so the drone starts armed (only the radio arms otherwise).
# The keyboard publishes on /cmd/manual; safety_manager forwards it to fc_bridge.

SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPTS/../.." && pwd)"   # compose.yaml lives here
source "$SCRIPTS/open_tabs.sh"

# Which view the Gazebo window shows (sim.launch.py camera:=...).
PS3="Select the camera (1-3): "
select cam in "FPV (the drone's front camera)" "Follow mode (behind the drone)" "Normal camera (free)"; do
    case $REPLY in
        1) CAMERA=fpv; break ;;
        2) CAMERA=follow; break ;;
        3) CAMERA=free; break ;;
        *) echo "Invalid option: $REPLY. Choose a number between 1 and 3." ;;
    esac
done

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_GAZEBO="cd '$REPO_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none radio:=false world:=room_world.sdf camera:=$CAMERA'"
CMD_KEYBOARD="cd '$REPO_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/cmd/manual'"

# Closes older sim processes, avoiding duplicates
bash "$SCRIPTS/stop_sim.sh"

open_tabs "Gazebo Sim" "$CMD_GAZEBO" \
          "Keyboard Teleop" "$CMD_KEYBOARD"
