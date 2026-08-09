#!/bin/bash
# report the state of the GUI automation harness
set -uo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"

report() {
    local name="$1"
    local port="${2:-}"
    if gui_pid_alive "$name"; then
        local state="running (pid $(cat "$HYPERTTS_GUI_PID_DIR/$name.pid"))"
    else
        local state="stopped"
    fi
    if [ -n "$port" ]; then
        if gui_port_in_use "$port"; then
            state="$state, port $port answering"
        else
            state="$state, port $port NOT answering"
        fi
    fi
    printf '%-12s %s\n' "$name" "$state"
}

echo "workdir: $HYPERTTS_GUI_WORKDIR"
echo "display: $HYPERTTS_GUI_DISPLAY"
report xvfb
report openbox
report x11vnc "$HYPERTTS_GUI_VNC_PORT"
report novnc "$HYPERTTS_GUI_NOVNC_PORT"
report anki
printf '%-12s %s\n' probe "$(gui_port_in_use "$HYPERTTS_GUI_PROBE_PORT" && echo "port $HYPERTTS_GUI_PROBE_PORT answering" || echo "port $HYPERTTS_GUI_PROBE_PORT not answering")"
printf '%-12s %s\n' ankiconnect "$(gui_port_in_use "$HYPERTTS_GUI_ANKICONNECT_PORT" && echo "port $HYPERTTS_GUI_ANKICONNECT_PORT answering" || echo "port $HYPERTTS_GUI_ANKICONNECT_PORT not answering")"

if gui_pid_alive xvfb; then
    echo
    echo "windows on $HYPERTTS_GUI_DISPLAY:"
    DISPLAY="$HYPERTTS_GUI_DISPLAY" wmctrl -l 2>/dev/null || echo "  (wmctrl failed)"
fi
