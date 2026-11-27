#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (joystick)                #
# ---------------------------------------------------------------------------- #

set -e

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

# The launch starts joy_node and radio_teleop itself (source:=joy is gone).
# SA arms (throttle centred), the takeover switch hands over the sticks.
CMD_GAZEBO_JOY="cd '$REPO_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none camera:=$CAMERA'"

# Closes older sim processes, avoiding duplicates
bash "$SCRIPTS/stop_sim.sh"

open_tabs "Gazebo Joy Sim" "$CMD_GAZEBO_JOY"
