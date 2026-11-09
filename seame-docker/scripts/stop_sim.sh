#!/bin/bash
# Stop any simulation still running in the dev container: the launch, its
# nodes, Gazebo and the teleops. Closing a terminal tab does not stop them:
# docker compose exec leaves its process running when the client goes away.
# The [x]yz patterns keep pkill from matching this command line itself.

cd "$(dirname "$0")/.."
docker compose exec -T dev bash -c '
  pkill -INT -f "[r]os2 launch drone_bringup"
  pkill -f "[t]eleop_twist_keyboard"
  pkill -f "[r]adio_teleop"
  sleep 2
  pkill -f "[g]z sim"
  pkill -f "[p]arameter_bridge"
  pkill -f "[f]c_bridge"
  pkill -f "[s]afety_manager"
  pkill -f "[f]low_model"
  pkill -f "[j]oy_node"
  # Wait until Gazebo is really gone: a new launch refuses to start while one runs.
  for i in $(seq 1 20); do pgrep -f "[g]z sim" >/dev/null || break; sleep 0.5; done
  pkill -9 -f "[g]z sim"
  true
' || true