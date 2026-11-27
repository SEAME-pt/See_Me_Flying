#!/bin/bash
# ---------------------------------------------------------------------------- #
#   Grafana through the Pi's USB ESP: make pi-esp-on / pi-esp-off / pi-esp-status #
# ---------------------------------------------------------------------------- #
# Run on the Pi (the ground station), from the repo root, through the Makefile.
#
#   on      msp_gateway on the USB bridge (firmware/pi_bridge) on :5760, then the
#           drone stack in the dev container: backend:=inav, listen-only,
#           source:=none, fc_bridge talking to the gateway. metrics_exporter
#           feeds Prometheus, so the Grafana dashboard fills in.
#   off     stops the stack, then the gateway (only if this script started it).
#           Grafana and Prometheus keep running with the history (make monitor-stop).
#   status  what is running and whether fc_bridge reaches the FC.
#
# One path per session: "on" refuses while any fc_bridge runs (a sim, a bench run,
# another drone stack): two metrics exporters can't share port 9105 and two MSP
# masters can't share the FC. Nothing here can stop a laptop joining the drone's
# Wi-Fi and talking to esp-link directly, so don't, while this is on.
#
# If an msp_gateway already listens on :5760 (started by hand, say), "on" uses
# it instead of starting another, and "off" leaves it running.
#
# Environment, all optional:
#   ESP_SERIAL     the bridge's device (default: the only /dev/serial/by-id/usb-1a86_*)
#   ESP_BAUD       default 115200, pi_bridge.ino's USB_BAUD
#   GATEWAY_PORT   default 5760
#   MSP_TIMEOUT_S  fc_bridge's wait for a cycle's replies (default 0.4: the gateway
#                  queues other clients' requests in front of ours)

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPTS_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

GW_SRC=project/telemetry/msp_dashboard
GW_BIN="$GW_SRC/build/msp_gateway"
STATE_DIR=/tmp/seame-pi-esp          # on the Pi: the gateway's pid and screen log
GW_PID="$STATE_DIR/gateway.pid"
GW_LOG="$STATE_DIR/gateway.log"
STACK_LOG=/tmp/pi_esp_stack.log      # in the container
PORT="${GATEWAY_PORT:-5760}"
BAUD="${ESP_BAUD:-115200}"
TIMEOUT="${MSP_TIMEOUT_S:-0.4}"
METRICS=http://127.0.0.1:9105/metrics
INSTALL=/home/dev/ros2_ws/install    # the workspace build, in the container
# How off and status find our launch among the container's processes.
# [s]: the pattern must not match the shell running pgrep/pkill itself.
STACK_PATTERN="[s]im.launch.py backend:=inav msp_host:=127.0.0.1"

say()  { echo "$*"; }
fail() { echo "Error: $*" >&2; exit 2; }

listening() { ss -Hltn "sport = :$1" 2>/dev/null | grep -q .; }
our_gateway() { [ -f "$GW_PID" ] && kill -0 "$(cat "$GW_PID")" 2>/dev/null; }
dev_running() { [ -n "$(docker compose ps -q --status running dev 2>/dev/null)" ]; }
in_dev() {   # stdin from /dev/null: docker would eat the terminal otherwise
    docker compose exec -T dev bash -c "source /opt/ros/jazzy/setup.bash && \
source $INSTALL/setup.bash && $1" < /dev/null
}
stack_running() { dev_running && in_dev "pgrep -f '$STACK_PATTERN' > /dev/null"; }
link_ok() { curl -fs --max-time 2 "$METRICS" 2>/dev/null | grep -q '^drone_link_ok 1'; }

find_serial() {
    if [ -n "${ESP_SERIAL:-}" ]; then
        [ -e "$ESP_SERIAL" ] || fail "ESP_SERIAL=$ESP_SERIAL doesn't exist"
        echo "$ESP_SERIAL"; return
    fi
    shopt -s nullglob
    local found=(/dev/serial/by-id/usb-1a86_*)
    shopt -u nullglob
    case ${#found[@]} in
        0) fail "No USB bridge found. Plug in the D1 Mini running firmware/pi_bridge,
       or set ESP_SERIAL=/dev/ttyUSB0" ;;
        1) echo "${found[0]}" ;;
        *) fail "Several CH340 devices: ${found[*]}
       Pick one: make pi-esp-on ESP_SERIAL=/dev/serial/by-id/..." ;;
    esac
}

build_gateway() {
    command -v cmake > /dev/null && command -v g++ > /dev/null ||
        fail "msp_gateway needs CMake and g++ on the Pi: sudo apt install cmake g++"
    [ -f "$GW_SRC/build/CMakeCache.txt" ] || cmake -S "$GW_SRC" -B "$GW_SRC/build" > /dev/null
    cmake --build "$GW_SRC/build" --target msp_gateway -j > /dev/null   # quick when up to date
}

start_gateway() {
    if listening "$PORT"; then
        our_gateway && say "msp_gateway already running (this script's)" ||
            say "Using the msp_gateway already listening on :$PORT (off will leave it running)"
        return
    fi
    local dev; dev=$(find_serial)
    [ -r "$dev" ] && [ -w "$dev" ] ||
        fail "No access to $dev. Add yourself to dialout: sudo usermod -aG dialout \$USER,
       then log out and in again"
    build_gateway
    mkdir -p "$STATE_DIR"
    # --log -: no per-frame JSON file. This runs for hours on the SD card.
    setsid nohup "$GW_BIN" --serial "$dev" --baud "$BAUD" --listen-port "$PORT" --log - \
        > "$GW_LOG" 2>&1 < /dev/null &
    echo $! > "$GW_PID"
    for _ in $(seq 50); do listening "$PORT" && break; sleep 0.1; done
    if ! listening "$PORT"; then
        tail -n 20 "$GW_LOG" >&2 || true
        rm -f "$GW_PID"
        fail "msp_gateway didn't start (its log is above)"
    fi
    say "msp_gateway on :$PORT, bridge $dev"
}

stop_gateway() {
    if ! our_gateway; then
        rm -f "$GW_PID"
        if listening "$PORT"; then say "msp_gateway on :$PORT wasn't started here: left running"; fi
        return 0
    fi
    local pid; pid=$(cat "$GW_PID")
    kill -INT "$pid" 2>/dev/null || true   # it stops any motors its clients left spinning
    for _ in $(seq 30); do kill -0 "$pid" 2>/dev/null || break; sleep 0.1; done
    kill -0 "$pid" 2>/dev/null && kill -TERM "$pid" 2>/dev/null || true
    rm -f "$GW_PID"
    say "msp_gateway stopped"
}

start_stack() {
    if stack_running; then say "Drone stack already running"; return; fi
    docker compose exec -d dev bash -c "source /opt/ros/jazzy/setup.bash && \
source $INSTALL/setup.bash && exec ros2 launch drone_bringup sim.launch.py \
backend:=inav msp_host:=127.0.0.1 msp_port:=$PORT msp_timeout_s:=$TIMEOUT source:=none \
> $STACK_LOG 2>&1"
    say "Drone stack started (backend inav, listen-only, through the gateway)"
}

stop_stack() {
    dev_running || return 0
    stack_running || return 0
    in_dev "pkill -INT -f '$STACK_PATTERN'" || true
    for _ in $(seq 100); do stack_running || break; sleep 0.1; done
    stack_running && in_dev "pkill -TERM -f '$STACK_PATTERN'" || true
    say "Drone stack stopped"
}

cmd_on() {
    dev_running || fail "The dev container isn't running (make pi-esp-on starts it: use make)"
    if ! stack_running; then
        in_dev "pgrep -x fc_bridge > /dev/null" &&
            fail "An fc_bridge is already running (a sim, a bench run or another drone stack).
       One path per session: stop it first (make sim-stop)"
        listening 9105 &&
            fail "Port 9105 is taken: another metrics_exporter is running. Stop it first"
    fi
    start_gateway
    start_stack
    printf "Waiting for the FC "
    for _ in $(seq 20); do link_ok && break; printf .; sleep 1; done
    echo
    if link_ok; then
        say "Link OK: Grafana is reading the drone."
    else
        say "No link to the FC yet. Check the D1 Mini's LED (solid = bridging), that the drone"
        say "is powered, then: make pi-esp-status. Logs: $GW_LOG (Pi), $STACK_LOG (container)"
    fi
    say "Dashboard: http://$(hostname -I | awk '{print $1}'):3000"
    say "Remember: no laptop on the drone's Wi-Fi while this is on. Stop with make pi-esp-off"
}

cmd_off() {
    stop_stack
    stop_gateway
    say "Off. Grafana keeps the history (make monitor-stop stops it)."
}

cmd_status() {
    if our_gateway; then say "msp_gateway   running (pid $(cat "$GW_PID")), log $GW_LOG"
    elif listening "$PORT"; then say "msp_gateway   something else listens on :$PORT"
    else say "msp_gateway   off"; fi
    if stack_running; then say "drone stack   running, log $STACK_LOG in the container"
    else say "drone stack   off"; fi
    if link_ok; then say "FC link       OK"
    elif curl -fs --max-time 2 "$METRICS" > /dev/null 2>&1; then say "FC link       DOWN (exporter up, no state from the FC)"
    else say "FC link       no metrics_exporter on :9105"; fi
    if listening 3000; then say "Grafana       http://$(hostname -I | awk '{print $1}'):3000"
    else say "Grafana       off (make monitor)"; fi
}

case "${1:-}" in
    on) cmd_on ;;
    off) cmd_off ;;
    status) cmd_status ;;
    *) echo "usage: $0 on|off|status"; exit 2 ;;
esac
