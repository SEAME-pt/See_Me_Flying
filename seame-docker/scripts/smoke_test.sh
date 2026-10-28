#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
source "$PROJECT_DIR/scripts/open_tabs.sh"

CMD_PUB="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_py setpoint_pub'"
CMD_WATCHDOG="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 run drone_basics_cpp watchdog'"
CMD_HZ="cd '$PROJECT_DIR' && docker compose exec dev bash -c 'cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && source install/setup.bash && ros2 topic hz /setpoint_velocity'"

open_tabs "Setpoint Publisher" "$CMD_PUB" \
          "Watchdog" "$CMD_WATCHDOG" \
          "Topic HZ" "$CMD_HZ"
