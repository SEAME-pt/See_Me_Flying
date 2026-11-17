#!/bin/bash
# ---------------------------------------------------------------------------- #
#   The motors play a melody through ROS: PROPS OFF, armed from the radio       #
# ---------------------------------------------------------------------------- #
# sing.py publishes the notes on /fc/setpoint_velocity; fc_bridge (rc_override)
# sends them to INAV as the throttle stick through MSP RC OVERRIDE (switch SA).
# This script runs the rest, like bench_rc_armed.sh: the bag, the bridge, the
# radio steps, and the laptop mic. No internet needed.
#
# Usage, on the host in seame-docker/, dev container running:
#   INSTALL=/tmp/inav6_bench/install scripts/motor_music/sing.sh calibrate
#   INSTALL=/tmp/inav6_bench/install scripts/motor_music/sing.sh play SONG.rtttl [options]
# play options go to sing.py: --part all, --octave N, --nudge N (semitones).
# The pitch map is the latest calibration's (MAP=path/pitch.json for another).
#
# calibrate: throttle stick 1050-1400 in 8 steps, 2 s each, recorded; the
# pitch of each step goes to pitch.json. play: the song, recorded.
# Everything into logs/measurements/motor_music/<date>_<commit>/.
#
# Kill switch: the radio's arm switch. If sing.py stops while SA is on,
# fc_bridge centres the throttle (1500): disarm.

MODE="${1:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
case "$MODE" in
    calibrate) shift ;;
    play)
        SONG="${2:-}"
        [ -f "$SONG" ] || { echo "❌ play needs an RTTTL file"; exit 2; }
        shift 2
        MAP="${MAP:-$(ls -t "$PROJECT"/logs/measurements/motor_music/*/pitch.json 2>/dev/null | head -1)}"
        [ -f "$MAP" ] || { echo "❌ No pitch map: run calibrate first (or MAP=...)"; exit 2; }
        echo "Pitch map: ${MAP#"$PROJECT"/}"
        python3 "$HERE/sing.py" play "$SONG" --map "$MAP" --dry-run "$@" || exit 2
        ;;
    *) echo "Usage: $0 calibrate | play SONG.rtttl [options]"; exit 2 ;;
esac

BENCH_NAME=motor_music
BENCH_NOTE="motor music $MODE through ROS (fc/setpoint_velocity, fc_bridge rc_override), \
PROPS OFF, armed from the radio, laptop on the drone AP"
source "$HERE/../bench_common.sh"
LOOK_ARMED_OK=armed-ok

# sing.py and what it needs, into the container.
docker compose cp "$HERE/sing.py" "dev:$TMP/sing.py" > /dev/null 2>&1
docker compose cp "$HERE/rtttl.py" "dev:$TMP/rtttl.py" > /dev/null 2>&1
docker compose cp "$HERE/analyse.py" "dev:$TMP/analyse.py" > /dev/null 2>&1
SING_ARGS="$MODE --tmp $TMP"
if [ "$MODE" = play ]; then
    docker compose cp "$SONG" "dev:$TMP/song.rtttl" > /dev/null 2>&1
    docker compose cp "$MAP" "dev:$TMP/map.json" > /dev/null 2>&1
    cp "$SONG" "$RUN/song.rtttl"
    cp "$MAP" "$RUN/map.json"
    SING_ARGS="play $TMP/song.rtttl --map $TMP/map.json --tmp $TMP $*"
fi
WAV="$RUN/$([ "$MODE" = calibrate ] && echo calib || echo song).wav"
REC=""

stop_rec() {
    if [ -n "$REC" ]; then
        kill -INT "$REC" 2>/dev/null || true
        wait "$REC" 2>/dev/null || true
        REC=""
    fi
}
bench_stop() {
    # The bridge first: its frames stop and INAV goes back to the radio. The
    # player last: without it the bridge would send throttle 1500.
    stop_bridge
    mark "sing stop"
    in_dev "pkill -INT -f '[s]ing.py $MODE'" || true
    stop_bag
    stop_rec
    bench_save
    echo "⚠️  If the drone is still armed: DISARM on the radio."
}
trap 'bench_stop; exit 130' INT

echo
echo "Setup: PROPS OFF, drone held level or strapped down, battery in, radio on"
echo "and bound, SA OFF, arm switch OFF, throttle low, INAV Configurator closed."
echo "Mic: the laptop, about 30 cm from the drone. Kill switch: the arm switch."
ask "Join the laptop to the drone's Wi-Fi (192.168.4.1)"

start_bag
mark "sing start (idle)"
in_dev_bg "exec python3 $TMP/sing.py $SING_ARGS >> $TMP/sing.log 2>&1"
sleep 3   # sing.py is publishing idle before the bridge starts
start_bridge true
sleep 4
look "connected (expect armed False, throttle 1000)"

echo
read -r -p "👉 Look at all four motors. Type 'props off' if there is no propeller on any: " reply
if [ "$reply" != "props off" ]; then
    echo "Not confirmed: stopping."
    bench_stop
    exit 1
fi
mark "props off confirmed"

ask "SA OFF, throttle low: ARM on the radio. Keep a hand near the arm switch"
sleep 1
look "armed on the radio (expect armed True)"
ask "Flip SA ON. ROS holds idle: the motors should not change"
sleep 2
look "SA on (expect throttle 1000, override_active True)"

arecord -q -D "${MIC:-default}" -f S16_LE -r 44100 -c 1 "$WAV" < /dev/null &
REC=$!
sleep 0.3
echo "{\"start_epoch\": $(date +%s.%N)}" > "$RUN/recording.json"
sleep 0.7
mark "go"
in_dev "touch $TMP/go"
echo "   🎵 ..."
for _ in $(seq 1 120); do
    in_dev "test -f $TMP/done" && break
    sleep 0.5
done
mark "done"
sleep 1
stop_rec
look "after (expect throttle 1000)"

ask "Flip SA OFF"
ask "DISARM on the radio"
sleep 1
look "disarmed (expect armed False)"

if [ "$MODE" = calibrate ]; then
    docker compose cp "$WAV" "dev:$TMP/calib.wav" > /dev/null 2>&1
    docker compose cp "$RUN/recording.json" "dev:$TMP/recording.json" > /dev/null 2>&1
    echo
    echo "Pitch of each throttle step:"
    in_dev "cd $TMP && python3 analyse.py $TMP" || echo "❌ analysis failed: tell Claude"
fi

bench_stop
echo "Rejoin your normal network, then tell Claude how it sounded."
