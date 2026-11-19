#!/bin/bash
# ---------------------------------------------------------------------------- #
#   Shared by the INAV bench scripts (bench_rc_override.sh, bench_rc_armed.sh)  #
# ---------------------------------------------------------------------------- #
# Sourced, not run. Before sourcing, set BENCH_NOTE (goes into meta.json), and
# BENCH_NAME for a run folder other than logs/measurements/inav_rc_override/.
# Sets PROJECT_DIR, RUN (the run folder), TMP (a folder in the container,
# copied into RUN by bench_save) and EVENTS, and gives the helpers below.
#
# Environment, all optional:
#   INSTALL   the build in the container (default: the workspace's own)
#   MSP_HOST, MSP_PORT   esp-link by default; another host/port to dry-run
#                        against a fake INAV

set -euo pipefail

<<<<<<< HEAD:project/scripts/bench_common.sh
SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPTS_DIR/../.." && pwd)"   # the repo root: compose.yaml; logs go to project/logs/
=======
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
cd "$PROJECT_DIR"
INSTALL="${INSTALL:-/home/dev/ros2_ws/install}"   # inside the container
MSP_HOST="${MSP_HOST:-192.168.4.1}"
MSP_PORT="${MSP_PORT:-23}"

if [ -z "$(docker compose ps -q --status running dev)" ]; then
<<<<<<< HEAD:project/scripts/bench_common.sh
    echo "Error: The dev container isn't running. Start it: make up"
    exit 2
fi
if ! docker compose exec -T dev test -f "$INSTALL/setup.bash" < /dev/null; then
    echo "Error: No build at $INSTALL in the container (set INSTALL=...)"
=======
    echo "❌ The dev container isn't running. Start it: docker compose up -d"
    exit 2
fi
if ! docker compose exec -T dev test -f "$INSTALL/setup.bash" < /dev/null; then
    echo "❌ No build at $INSTALL in the container (set INSTALL=...)"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
    exit 2
fi

RUN=$(BENCH_NAME="${BENCH_NAME:-inav_rc_override}" BENCH_NOTE="$BENCH_NOTE, install $INSTALL" python3 -c "import os, sys; \
<<<<<<< HEAD:project/scripts/bench_common.sh
sys.path.insert(0, '$SCRIPTS_DIR'); from logbook import new_run; \
print(new_run('measurements', os.environ['BENCH_NAME'], {'note': os.environ['BENCH_NOTE']}))")
TMP="/tmp/inav6_rc_$(date +%s)"
EVENTS="$RUN/events.log"
echo "Results in ${RUN#"$PROJECT_DIR"/}"
=======
sys.path.insert(0, 'scripts'); from logbook import new_run; \
print(new_run('measurements', os.environ['BENCH_NAME'], {'note': os.environ['BENCH_NOTE']}))")
TMP="/tmp/inav6_rc_$(date +%s)"
EVENTS="$RUN/events.log"
echo "📁 ${RUN#"$PROJECT_DIR"/}"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh

in_dev() {   # a command in the container, with ROS and the build sourced
    # stdin from /dev/null: docker would otherwise eat the Enter meant for ask.
    docker compose exec -T dev bash -c "source /opt/ros/jazzy/setup.bash && \
source $INSTALL/setup.bash && $1" < /dev/null
}
in_dev_bg() {
    docker compose exec -d dev bash -c "source /opt/ros/jazzy/setup.bash && \
source $INSTALL/setup.bash && $1"
}
mark() {
    echo "$(date +%s.%N) $*" >> "$EVENTS"
    echo
    echo "── $*"
}
ask() {   # what to do, then wait for Enter
    echo
<<<<<<< HEAD:project/scripts/bench_common.sh
    echo "> $*"
=======
    echo "👉 $*"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
    read -r -p "   Enter when done... " _
}

start_bridge() {   # $1: rc_override true or false
    mark "fc_bridge start, rc_override $1"
    in_dev_bg "exec ros2 run drone_fc_bridge fc_bridge --ros-args -p backend:=inav \
-p rc_override:=$1 -p msp_host:=$MSP_HOST -p msp_port:=$MSP_PORT >> $TMP/bridge.log 2>&1"
}
stop_bridge() {
    mark "fc_bridge stop"
    in_dev "pkill -INT -x fc_bridge; sleep 1" || true
}

# Setpoints, one way or the other. pub: one ros2 topic pub per setpoint
# (about 2 s to start, so gaps between them). feed: one publisher for the
# whole run at 20 Hz, whose setpoint set_sp changes, with no gaps.
pub() {   # $1: twist as YAML, $2: seconds
    mark "setpoint $1 for $2 s"
    in_dev_bg "exec timeout $2 ros2 topic pub -r 20 /fc/setpoint_velocity \
geometry_msgs/msg/TwistStamped '{twist: $1}' > /dev/null 2>&1"
}
stop_pub() {
    # [t]: the pattern must not match the shell running pkill itself.
    in_dev "pkill -f '[t]opic pub -r 20 /fc/setpoint_velocity'" || true
}
set_sp() {   # x y z yaw_rate, read by feed.py
    mark "setpoint x $1 y $2 z $3 yaw $4"
    in_dev "echo '$1 $2 $3 $4' > $TMP/setpoint.tmp && mv $TMP/setpoint.tmp $TMP/setpoint"
}
start_feed() {
    mark "feed start"
    in_dev_bg "exec python3 $TMP/feed.py $TMP/setpoint >> $TMP/feed.log 2>&1"
}
stop_feed() {
    mark "feed stop"
    in_dev "pkill -INT -f '[f]eed.py $TMP'" || true
}

start_bag() {
    mark "bag start"
    in_dev_bg "exec ros2 bag record -s mcap -o $TMP/bag /fc/rc /fc/motors /fc/status \
/fc/setpoint_velocity /fc/attitude > $TMP/bag.log 2>&1"
}
stop_bag() {
    mark "bag stop"
    in_dev "pkill -INT -f '[r]os2 bag record'; sleep 2" || true
}
bench_save() {
    docker compose cp "dev:$TMP/." "$RUN/" > /dev/null 2>&1
    # The helper scripts and go/done flags are copies or empty: not results.
    (cd "$RUN" && rm -rf -- *.py __pycache__ go done)
    echo
<<<<<<< HEAD:project/scripts/bench_common.sh
    echo "Saved in ${RUN#"$PROJECT_DIR"/}: bag/, events.log, bridge.log, bag.log"
=======
    echo "✅ Saved in ${RUN#"$PROJECT_DIR"/}: bag/, events.log, bridge.log, bag.log"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
}

# Prints fc/rc, fc/motors and fc/status on one line. With LOOK_ARMED_OK unset,
# an armed drone stops the run (bench_stop, defined by the script).
look() {   # $1: label
    local out
    out=$(in_dev "python3 $TMP/look.py ${LOOK_ARMED_OK:-}" 2>&1) || {
        echo "$out"
<<<<<<< HEAD:project/scripts/bench_common.sh
        echo "STOP: armed, stopping."
=======
        echo "🛑 Armed: stopping."
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
        bench_stop
        exit 1
    }
    echo "   $out"
    echo "$(date +%s.%N) LOOK $1: $out" >> "$EVENTS"
}

# The first readout, but waiting (about 20 s) for the FC to answer through
# esp-link; stops the run if it never does.
wait_link() {   # $1: label
    local out
    for _ in 1 2 3 4 5 6; do
        out=$(in_dev "python3 $TMP/look.py armed-ok" 2>&1) || true
        if [[ "$out" == *"link_ok True"* ]]; then
            look "$1"
            return 0
        fi
<<<<<<< HEAD:project/scripts/bench_common.sh
        echo "   waiting for the FC to answer through esp-link..."
    done
    echo "$(date +%s.%N) LOOK $1: $out" >> "$EVENTS"
    echo "STOP: The ESP answers but INAV doesn't (or the laptop isn't on the drone's Wi-Fi):"
=======
        echo "   ⏳ waiting for the FC to answer through esp-link..."
    done
    echo "$(date +%s.%N) LOOK $1: $out" >> "$EVENTS"
    echo "🛑 The ESP answers but INAV doesn't (or the laptop isn't on the drone's Wi-Fi):"
>>>>>>> origin/main:seame-docker/scripts/bench_common.sh
    echo "   power-cycle the drone (battery out, in, keep it still) and run again."
    bench_stop
    exit 1
}

# Leftovers of an earlier run that was cut short.
in_dev "pkill -f '[t]opic pub -r 20 /fc/setpoint_velocity'; pkill -INT -f '[f]eed.py'; \
pkill -INT -f '[s]ing.py'; \
pkill -INT -x fc_bridge; pkill -INT -f '[r]os2 bag record'; sleep 1" || true

docker compose exec -T dev bash -c "mkdir -p $TMP && cat > $TMP/look.py" <<'EOF'
import sys
import time

from drone_interfaces.msg import FcStatus, MotorOutputs, RcChannels
import rclpy

armed_ok = 'armed-ok' in sys.argv
rclpy.init()
node = rclpy.create_node('bench_look')
got = {}
node.create_subscription(RcChannels, '/fc/rc', lambda m: got.setdefault('rc', m), 10)
node.create_subscription(MotorOutputs, '/fc/motors', lambda m: got.setdefault('mo', m), 10)
node.create_subscription(FcStatus, '/fc/status', lambda m: got.setdefault('st', m), 10)
end = time.monotonic() + 3.0
while time.monotonic() < end and len(got) < 3:
    rclpy.spin_once(node, timeout_sec=0.1)
line = []
if 'rc' in got:
    r = got['rc']
    ch7 = r.channels[6] if len(r.channels) > 6 else 0
    line.append(f'fc/rc roll {r.roll} pitch {r.pitch} yaw {r.yaw} throttle {r.throttle} '
                f'ch7(SA) {ch7}')
else:
    line.append('fc/rc: nothing in 3 s')
line.append('motors ' + ' '.join(str(v) for v in got['mo'].motors) if 'mo' in got
            else 'fc/motors: nothing')
if 'st' in got:
    s = got['st']
    line.append(f'override_active {s.rc_override_active} rc_sent {s.rc_sent} '
                f'link_ok {s.link_ok} armed {s.armed}')
else:
    line.append('fc/status: nothing in 3 s')
print(' | '.join(line))
if 'st' in got and got['st'].armed and not armed_ok:
    print('ARMED: disarm now')
    sys.exit(3)
EOF

# Publishes the setpoint in the file (x y z yaw_rate) at 20 Hz until stopped.
# Nothing until it has read one (zero would be throttle 1500); after that a
# file it can't read keeps the last setpoint. It never stops on its own.
docker compose exec -T dev bash -c "cat > $TMP/feed.py" <<'EOF'
import sys

from geometry_msgs.msg import TwistStamped
import rclpy

path = sys.argv[1]
rclpy.init()
node = rclpy.create_node('bench_feed')
pub = node.create_publisher(TwistStamped, '/fc/setpoint_velocity', 10)
last = []


def tick():
    try:
        with open(path) as f:
            values = [float(v) for v in f.read().split()]
        if len(values) == 4:
            last[:] = values
    except (OSError, ValueError):
        pass
    if not last:
        return
    msg = TwistStamped()
    msg.header.stamp = node.get_clock().now().to_msg()
    msg.header.frame_id = 'base_link'
    msg.twist.linear.x, msg.twist.linear.y, msg.twist.linear.z, msg.twist.angular.z = last
    pub.publish(msg)


node.create_timer(0.05, tick)
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    pass
EOF
