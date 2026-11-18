#!/bin/bash
# ---------------------------------------------------------------------------- #
#   INAV-6 armed bench run: ROS drives the motors, PROPS OFF, short bursts      #
# ---------------------------------------------------------------------------- #
# The radio arms; ROS takes the sticks through MSP RC OVERRIDE (switch SA) and
# runs a throttle ramp and three direction tests, 3 s each, then gives the
# sticks back. Optionally, last: does INAV's failsafe cut the motors when the
# radio goes off with the override on? Bag (with fc/motors), events.log and
# logs into logs/measurements/inav_rc_override/<date>_<commit>/. No internet
# needed: start it, then join the drone's Wi-Fi when it says so.
#
# Usage, on the host in seame-docker/, dev container running:
#   INSTALL=/tmp/inav6_bench/install ./scripts/bench_rc_armed.sh
#
# Throttle is raw power here (ANGLE, no altitude hold): the setpoint's z maps
# to the throttle stick, -0.3 m/s (max_speed_z) = 1000 = idle, 0 = 1500 =
# about half power. One publisher sends the setpoint for the whole run, at
# idle until the ramp, so SA never switches onto a higher throttle. If ROS
# stops sending while SA is on, fc_bridge centres the sticks: throttle 1500.
# The kill switch is the radio's arm switch: arming follows the radio only,
# override or not.

BENCH_NOTE="bench, PROPS OFF, armed from the radio, laptop on the drone AP, fc_bridge backend \
inav rc_override, throttle ramp and directions"
source "$(dirname "$0")/bench_common.sh"
LOOK_ARMED_OK=armed-ok

IDLE="0 0 -0.3 0"   # throttle 1000
bench_stop() {
    # The bridge first: its frames stop and INAV goes back to the radio. The
    # feed last: without it the bridge would send throttle 1500.
    stop_bridge
    stop_feed
    stop_bag
    bench_save
    echo "⚠️  If the drone is still armed: DISARM on the radio."
}
trap 'bench_stop; exit 130' INT

echo
echo "Setup: PROPS OFF, drone held or strapped down, battery in, radio on and"
echo "bound, SA OFF, arm switch OFF, throttle low, INAV Configurator closed."
echo "Kill switch: the arm switch. Last resort: pull the battery."
ask "Join the laptop to the drone's Wi-Fi (192.168.4.1)"

start_bag
in_dev "echo '$IDLE' > $TMP/setpoint"   # before the feed starts: never a zero setpoint
start_feed
start_bridge true
sleep 4
wait_link "connected (expect armed False, rc_sent True)"

echo
read -r -p "👉 Look at all four motors. Type 'props off' if there is no propeller on any: " reply
if [ "$reply" != "props off" ]; then
    echo "Not confirmed: stopping."
    bench_stop
    exit 1
fi
mark "props off confirmed"

# 1. Armed on the radio: the radio's throttle, low.
ask "SA OFF, throttle low: ARM on the radio. Keep a hand near the arm switch"
sleep 1
look "1 armed on the radio (expect armed True, override_active False, motors idle)"

# 2. SA on: ROS takes over, still at idle.
mark "step 2: SA on at idle"
ask "Flip SA ON. ROS's throttle is idle too: the motors should not change"
sleep 2
look "2 SA on (expect throttle 1000, override_active True)"

# 3. Throttle ramp, 3 s each, back to idle.
mark "step 3: throttle ramp"
for z in -0.2 -0.1 0.0; do
    set_sp 0 0 "$z" 0
    sleep 1.5
    look "3 z $z (expect throttle $(python3 -c "print(round(1500 + 500 * $z / 0.3))"))"
    sleep 1
done
set_sp $IDLE
sleep 2

# 4. Directions at throttle 1333. Props off, INAV's stabilisation sees no
#    tilt come and keeps pushing: the motor pairs drift apart for as long as
#    the command lasts. That is expected.
mark "step 4: directions at throttle 1333"
for axis in "forward|0.25 0 -0.1 0|pitch 1750: the rear motors speed up" \
            "left|0 0.25 -0.1 0|roll 1250: the right motors speed up" \
            "yaw_left|0 0 -0.1 0.5|yaw 1250: one diagonal pair speeds up"; do
    IFS='|' read -r name sp want <<< "$axis"
    set_sp 0 0 -0.1 0
    sleep 2
    set_sp $sp
    sleep 1.5
    look "4 $name (expect $want)"
    sleep 1
done
set_sp $IDLE
sleep 2
look "4 back to idle (expect throttle 1000)"

# 5. Hand back and disarm.
mark "step 5: SA off, disarm"
ask "Flip SA OFF (the radio has the sticks again, throttle low)"
ask "DISARM on the radio"
sleep 1
look "5 disarmed (expect armed False, override_active False)"

# 6. Optional: the radio goes off with the override on.
echo
read -r -p "👉 Run the radio-off failsafe test (armed, SA on, idle, then radio off)? [y/N] " reply
if [ "$reply" = "y" ]; then
    mark "step 6: failsafe test"
    ask "Throttle low, SA OFF: ARM on the radio"
    ask "Flip SA ON (ROS at idle)"
    sleep 2
    look "6 armed, SA on, idle"
    mark "step 6: radio off"
    ask "Turn the RADIO OFF and watch the motors for 3 s. Enter after"
    look "6 radio off (do the motors stop? armed?)"
    stop_bridge   # the frames stop too: nothing of ROS left
    echo
    echo "⚠️  If the motors still spin: PULL THE BATTERY now."
    ask "Put the arm switch OFF and SA OFF, then turn the radio back on"
    start_bridge false
    sleep 4
    look "6 radio back (expect armed False)"
fi

bench_stop
echo "Rejoin your normal network, then tell Claude the run is done."
