
#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

CMD_PUB="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_py setpoint_pub'"
CMD_WATCHDOG="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_cpp watchdog'"
CMD_HZ="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 topic hz /setpoint_velocity'"

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