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
<<<<<<< HEAD:project/scripts/bench_rc_override.sh
# Usage, from the repo root, dev container running (make up):
#   make bench-rc
#   make bench-rc INSTALL=/tmp/inav6_bench/install   # another build
=======
# Usage, on the host in seame-docker/, dev container running:
#   ./scripts/bench_rc_override.sh
#   INSTALL=/tmp/inav6_bench/install ./scripts/bench_rc_override.sh   # another build
>>>>>>> origin/main:seame-docker/scripts/bench_rc_override.sh
#
# Safety: the drone must stay disarmed. The script stops everything if
# fc/status ever reports armed. ROS can't arm it: only the four stick
# channels are overridden, never AUX1.

BENCH_NOTE="bench, props off, unarmed, laptop on the drone AP, fc_bridge backend inav rc_override"
source "$(dirname "$0")/bench_common.sh"

bench_stop() {
    stop_pub
    stop_bridge
    stop_bag
    bench_save
}
trap 'bench_stop; exit 130' INT

echo
echo "Setup: props OFF, battery in, radio on and bound, SA OFF, arm switch OFF"
echo "for the whole run, INAV Configurator closed, USB unplugged."
ask "Join the laptop to the drone's Wi-Fi (192.168.4.1)"

start_bag
start_bridge true
sleep 4
wait_link "connected"

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

bench_stop
echo "Rejoin your normal network, then tell Claude the run is done."
