<<<<<<< HEAD

=======
>>>>>>> bdf61fc24b8907b23dc8e021c0284302c5e327b8
#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
<<<<<<< HEAD
=======
source "$PROJECT_DIR/scripts/open_tabs.sh"
>>>>>>> bdf61fc24b8907b23dc8e021c0284302c5e327b8

CMD_PUB="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_py setpoint_pub'"
CMD_WATCHDOG="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_cpp watchdog'"
CMD_HZ="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 topic hz /setpoint_velocity'"

<<<<<<< HEAD
if command -v wt.exe >/dev/null 2>&1; then
    wt.exe -w 0 new-tab wsl.exe -d Ubuntu bash -c "$CMD_PUB" \; \
           new-tab wsl.exe -d Ubuntu bash -c "$CMD_WATCHDOG" \; \
           new-tab wsl.exe -d Ubuntu bash -c "$CMD_HZ"
elif command -v gnome-terminal >/dev/null 2>&1; then
    gnome-terminal --tab --title="Setpoint Publisher" -- bash -c "$CMD_PUB"
    gnome-terminal --tab --title="Watchdog" -- bash -c "$CMD_WATCHDOG"
    gnome-terminal --tab --title="Topic HZ" -- bash -c "$CMD_HZ"
else
    echo "❌ Neither wt.exe nor gnome-terminal was found."
    exit 1
fi
=======
open_tabs "Setpoint Publisher" "$CMD_PUB" \
          "Watchdog" "$CMD_WATCHDOG" \
          "Topic HZ" "$CMD_HZ"
>>>>>>> bdf61fc24b8907b23dc8e021c0284302c5e327b8
