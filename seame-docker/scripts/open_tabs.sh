#!/bin/bash
# ---------------------------------------------------------------------------- #
#        Helper: open each command in its own terminal tab (sourced)           #
# ---------------------------------------------------------------------------- #
# Usage: open_tabs "Title 1" "command 1" "Title 2" "command 2" ...
#
# Supports Windows Terminal (WSL), gnome-terminal, ptyxis (Ubuntu 25.10+),
# konsole and any x-terminal-emulator. Tabs stay open after the command ends,
# so a failure shows its error instead of the tab vanishing.

# Keeps the tab open and shows the exit code. No ';' on purpose: wt.exe splits on it.
_hold() {
    echo "($1) || echo \"⚠️  Exited with code \$?\" && echo && read -rp 'Press Enter to close this tab...'"
}

open_tabs() {
    local args=() title cmd

    if command -v wt.exe >/dev/null 2>&1; then
        args=(-w 0)
        while [ $# -gt 0 ]; do
            [ ${#args[@]} -gt 2 ] && args+=(\;)
            args+=(new-tab --title "$1" wsl.exe -d "${WSL_DISTRO_NAME:-Ubuntu}" bash -c "$(_hold "$2")")
            shift 2
        done
        wt.exe "${args[@]}"
        return
    fi

    local term=""
    for t in gnome-terminal ptyxis konsole x-terminal-emulator xterm; do
        if command -v "$t" >/dev/null 2>&1; then term=$t; break; fi
    done

    if [ -z "$term" ] || [ -z "$DISPLAY$WAYLAND_DISPLAY" ]; then
        echo "❌ No graphical terminal available (tried wt.exe, gnome-terminal, ptyxis, konsole, xterm)."
        echo "   Run each of these in its own terminal instead:"
        while [ $# -gt 0 ]; do
            echo -e "\n# $1\n$2"
            shift 2
        done
        return 1
    fi

    while [ $# -gt 0 ]; do
        title=$1
        cmd=$(_hold "$2")
        case $term in
            gnome-terminal) gnome-terminal --tab --title="$title" -- bash -c "$cmd" ;;
            ptyxis)         ptyxis --tab -T "$title" -- bash -c "$cmd" ;;
            konsole)        konsole --new-tab -p tabtitle="$title" -e bash -c "$cmd" >/dev/null 2>&1 & ;;
            *)              "$term" -T "$title" -e bash -c "$cmd" >/dev/null 2>&1 & ;;
        esac
        shift 2
    done
    echo "✅ Opened tabs in $term."
}
