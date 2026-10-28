# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (joystick)                #
# ---------------------------------------------------------------------------- #

#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_GAZEBO_JOY="cd '$PROJECT_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=joy'"
CMD_RADIO_TELEOP="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_py radio_teleop'"

if command -v wt.exe >/dev/null 2>&1; then
    wt.exe -w 0 new-tab wsl.exe -d Ubuntu bash -c "$CMD_GAZEBO_JOY" \; \
           new-tab wsl.exe -d Ubuntu bash -c "$CMD_RADIO_TELEOP"
elif command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --tab --title="Gazebo Joy Sim" -- bash -c "$CMD_GAZEBO_JOY"
    gnome-terminal --tab --title="Radio Teleop Node" -- bash -c "$CMD_RADIO_TELEOP"
else
    echo "❌ Neither wt.exe nor gnome-terminal was found."
    exit 1
fi