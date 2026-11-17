#!/bin/bash
# ---------------------------------------------------------------------------- #
#   INAV-6 bench run: ROS sticks through MSP RC OVERRIDE, props off, unarmed    #
# ---------------------------------------------------------------------------- #
# Walks through the run step by step: says what to do with the radio, sends
# the setpoints itself, prints what INAV uses (fc/rc) and fc/status after each
# step, and records a bag the whole time. Everything ends up in
# logs/measurements/inav_rc_override/<date>_<commit>/: the bag, events.log
# (a timestamped line per step), the bridge's log and each step's readout.
# Needs no internet: start it, then join the drone's Wi-Fi when it says so.
#
# Usage, on the host in seame-docker/, dev container running:
#   ./scripts/bench_rc_override.sh
#   INSTALL=/tmp/inav6_bench/install ./scripts/bench_rc_override.sh   # another build
#
# Safety: the drone must stay disarmed. The script stops everything if
# fc/status ever reports armed. ROS can't arm it: only the four stick
# channels are overridden, never AUX1.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"
INSTALL="${INSTALL:-/home/dev/ros2_ws/install}"   # inside the container
MSP_HOST="${MSP_HOST:-192.168.4.1}"   # esp-link; another host/port to dry-run against a fake
MSP_PORT="${MSP_PORT:-23}"

if [ -z "$(docker compose ps -q --status running dev)" ]; then
    echo "❌ The dev container isn't running. Start it: docker compose up -d"
    exit 2
fi
if ! docker compose exec -T dev test -f "$INSTALL/setup.bash"; then
    echo "❌ No build at $INSTALL in the container (set INSTALL=...)"
    exit 2
fi

RUN=$(python3 -c "import sys; sys.path.insert(0, 'scripts'); from logbook import new_run; \
print(new_run('measurements', 'inav_rc_override', {'note': 'bench, props off, unarmed, \
laptop on the drone AP, fc_bridge backend inav rc_override, install $INSTALL'}))")
TMP="/tmp/inav6_rc_$(date +%s)"   # in the container; copied into $RUN at the end
EVENTS="$RUN/events.log"
echo "📁 ${RUN#"$PROJECT_DIR"/}"

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
    echo "👉 $*"
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
pub() {   # $1: twist as YAML, $2: seconds
    mark "setpoint $1 for $2 s"
    in_dev_bg "exec timeout $2 ros2 topic pub -r 20 /fc/setpoint_velocity \
geometry_msgs/msg/TwistStamped '{twist: $1}' > /dev/null 2>&1"
}
stop_pub() {
    # [t]: the pattern must not match the shell running pkill itself.
    in_dev "pkill -f '[t]opic pub -r 20 /fc/setpoint_velocity'" || true
}
look() {   # $1: label. Prints one fc/rc and one fc/status; stops all if armed.
    local out
    out=$(in_dev "python3 $TMP/look.py" 2>&1) || {
        echo "$out"
        echo "🛑 Armed, or no data: stopping."
        finish
        exit 1
    }
    echo "   $out"
    echo "$(date +%s.%N) LOOK $1: $out" >> "$EVENTS"
}

finish() {
    stop_pub
    stop_bridge
    mark "bag stop"
    in_dev "pkill -INT -f '[r]os2 bag record'; sleep 2" || true
    docker compose cp "dev:$TMP/." "$RUN/" > /dev/null 2>&1
    echo
    echo "✅ Saved in ${RUN#"$PROJECT_DIR"/}: bag/, events.log, bridge.log, bag.log"
}

# Leftovers of an earlier run that was cut short.
stop_pub
in_dev "pkill -INT -x fc_bridge; pkill -INT -f '[r]os2 bag record'; sleep 1" || true
trap 'finish; exit 130' INT

# One fc/rc and one fc/status, on one line. Exit 3 if INAV reports armed.
docker compose exec -T dev bash -c "mkdir -p $TMP && cat > $TMP/look.py" <<'EOF'
import sys
import time

from drone_interfaces.msg import FcStatus, RcChannels
import rclpy

rclpy.init()
node = rclpy.create_node('bench_look')
got = {}
node.create_subscription(RcChannels, '/fc/rc', lambda m: got.setdefault('rc', m), 10)
node.create_subscription(FcStatus, '/fc/status', lambda m: got.setdefault('st', m), 10)
end = time.monotonic() + 3.0
while time.monotonic() < end and len(got) < 2:
    rclpy.spin_once(node, timeout_sec=0.1)
line = []
if 'rc' in got:
    r = got['rc']
    ch7 = r.channels[6] if len(r.channels) > 6 else 0
    line.append(f'fc/rc roll {r.roll} pitch {r.pitch} yaw {r.yaw} throttle {r.throttle} '
                f'ch7(SA) {ch7}')
else:
    line.append('fc/rc: nothing in 3 s')
if 'st' in got:
    s = got['st']
    line.append(f'override_active {s.rc_override_active} rc_sent {s.rc_sent} '
                f'link_ok {s.link_ok} armed {s.armed}')
else:
    line.append('fc/status: nothing in 3 s')
print(' | '.join(line))
if 'st' in got and got['st'].armed:
    print('ARMED: disarm now')
    sys.exit(3)
EOF

echo
echo "Setup: props OFF, battery in, radio on and bound, SA OFF, arm switch OFF"
echo "for the whole run, INAV Configurator closed, USB unplugged."
ask "Join the laptop to the drone's Wi-Fi (192.168.4.1)"

mark "bag start"
in_dev_bg "exec ros2 bag record -s mcap -o $TMP/bag /fc/rc /fc/status \
/fc/setpoint_velocity /fc/attitude > $TMP/bag.log 2>&1"
start_bridge true
sleep 4
look "connected"

# 1. Override off: the radio flies.
mark "step 1: SA off, radio sticks"
ask "SA OFF. Hold the right stick fully UP (pitch forward) and keep holding"
look "1 SA off, pitch stick up (expect pitch ~2000, override_active False)"
ask "Let go of the sticks"

# 2. Override on: ROS flies, the radio's sticks are ignored.
mark "step 2: SA on"
ask "Flip SA ON. Don't touch the sticks"
sleep 1
look "2 SA on, no setpoint (expect 1500 x4, override_active True)"
ask "Hold the right stick fully UP again and keep holding"
look "2 SA on, radio pitch up (expect pitch still 1500: radio ignored)"
ask "Let go of the sticks"
for axis in "forward|{linear: {x: 0.25}}|pitch 1750" "left|{linear: {y: 0.25}}|roll 1250" \
            "up|{linear: {z: 0.15}}|throttle 1750" "yaw_left|{angular: {z: 0.5}}|yaw 1250"; do
    IFS='|' read -r name twist want <<< "$axis"
    pub "$twist" 8   # ros2 topic pub takes about 2 s to start sending
    sleep 3.5
    look "2 $name (expect $want, the rest 1500)"
    sleep 5          # until it has stopped
done

# 3. Setpoints stop: centred after setpoint_timeout_s (0.3 s).
mark "step 3: setpoint timeout"
pub "{linear: {x: 0.25}}" 8
sleep 3.5
look "3 forward before the stop (expect pitch 1750)"
sleep 6
look "3 after the stop (expect 1500 x4)"

# 4. fc_bridge stops: INAV goes back to the radio about 0.9 s after the
#    last frame. A listen-only bridge reads it; the bag has the timing.
mark "step 4: bridge stops while sending pitch 1750"
pub "{linear: {x: 0.25}}" 30
sleep 3
stop_bridge
start_bridge false
sleep 4
look "4 listen-only bridge (expect pitch 1500: back to the radio)"
stop_pub
stop_bridge
start_bridge true
sleep 4

# 5. Wi-Fi drops: no frames, back to the radio; on reconnect, ROS again
#    after the override's start-up delay (about 0.7 s).
mark "step 5: Wi-Fi drop"
pub "{linear: {x: 0.25}}" 600   # stopped after step 6
sleep 3
look "5 before the drop (expect pitch 1750)"
mark "step 5: Wi-Fi off"
ask "Disconnect the laptop from the drone's Wi-Fi, count to 5, reconnect"
mark "step 5: Wi-Fi back"
sleep 6
look "5 after reconnecting (expect pitch 1750 again)"

# 6. Radio off with the override on.
mark "step 6: radio off, SA on"
ask "SA still ON. Turn the RADIO OFF"
sleep 2
look "6 radio off (note: does pitch stay 1750? override_active?)"
sleep 3
look "6 radio off, 5 s later"
stop_pub

# 7. Back to the radio.
ask "Turn the radio back ON, then flip SA OFF"
mark "step 7: radio on, SA off"
sleep 2
look "7 SA off (expect radio values, override_active False)"

finish
echo "Rejoin your normal network, then tell Claude the run is done."
