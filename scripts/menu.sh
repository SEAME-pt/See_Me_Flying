#!/bin/bash
#
# Interactive launcher for the SEA:ME ROS 2 development environment.

set -euo pipefail

cd "$(dirname "$0")/.."

# Colour only when writing to a terminal and NO_COLOR is not set.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    BOLD=$'\033[1m'
    DIM=$'\033[2m'
    RED=$'\033[31m'
    RESET=$'\033[0m'
else
    BOLD="" DIM="" RED="" RESET=""
fi

print_menu() {
    printf '\n%sSEA:ME ROS 2 - Development Environment%s\n\n' "$BOLD" "$RESET"
    printf '  1  %-12s %s%s%s\n' "Smoke test" "$DIM" "Publishers and watchdog"            "$RESET"
    printf '  2  %-12s %s%s%s\n' "Simulation" "$DIM" "Gazebo, keyboard control"           "$RESET"
    printf '  3  %-12s %s%s%s\n' "Simulation" "$DIM" "Gazebo, RadioMaster / joystick"     "$RESET"
    printf '  4  %-12s %s%s%s\n' "Shell"      "$DIM" "Interactive bash in the container"  "$RESET"
    printf '  q  Quit\n\n'
}

print_menu

while true; do
    read -rp "Select an option [1-4, q (quit)]: " choice || exit 0

    case "$choice" in
        1)
            echo "Starting smoke test..."
            exec bash scripts/smoke_test.sh
            ;;
        2)
            echo "Starting Gazebo with keyboard control..."
            exec bash scripts/sim_keyboard.sh
            ;;
        3)
            echo "Starting Gazebo with joystick control..."
            exec bash scripts/sim_joy.sh
            ;;
        4)
            exec docker compose exec dev bash
            ;;
        q|Q)
            exit 0
            ;;
        *)
            printf '%sInvalid option: %s%s\n' "$RED" "${choice:-<empty>}" "$RESET" >&2
            ;;
    esac
done
