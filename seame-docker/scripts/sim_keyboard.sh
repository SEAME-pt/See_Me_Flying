<<<<<<< HEAD
# ---------------------------------------------------------------------------- #
#               Script run gazebo simulator with ros2 (keyboard)               #
# ---------------------------------------------------------------------------- #

#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

CMD_GAZEBO="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none'"
CMD_KEYBOARD="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/fc/setpoint_velocity'"

if command -v wt.exe >/dev/null 2>&1; then
    wt.exe -w 0 new-tab wsl.exe -d Ubuntu bash -c "$CMD_GAZEBO" \; \
           new-tab wsl.exe -d Ubuntu bash -c "$CMD_KEYBOARD"
elif command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --tab --title="Gazebo Sim" -- bash -c "$CMD_GAZEBO"
    gnome-terminal --tab --title="Keyboard Teleop" -- bash -c "$CMD_KEYBOARD"
else
    echo "❌ Neither wt.exe nor gnome-terminal was found."
    exit 1
fi
=======
#!/bin/bash
# ---------------------------------------------------------------------------- #
#              Script run gazebo simulator with ros2 (keyboard)                #
# ---------------------------------------------------------------------------- #

set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/scripts/open_tabs.sh"

if command -v xhost >/dev/null 2>&1; then
    xhost +local:docker >/dev/null 2>&1 || true
fi

CMD_GAZEBO="cd '$PROJECT_DIR' && docker compose exec -e DISPLAY=\$DISPLAY dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 launch drone_bringup sim.launch.py source:=none'"
CMD_KEYBOARD="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -p frame_id:=base_link -p use_sim_time:=true -r cmd_vel:=/fc/setpoint_velocity'"

open_tabs "Gazebo Sim" "$CMD_GAZEBO" \
          "Keyboard Teleop" "$CMD_KEYBOARD"
>>>>>>> bdf61fc24b8907b23dc8e021c0284302c5e327b8
