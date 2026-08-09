#!/bin/bash
# start the virtual display stack: Xvfb + openbox window manager + x11vnc + noVNC
# idempotent: re-running when everything is already up is a no-op
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"

if gui_pid_alive xvfb; then
    gui_log "Xvfb already running on $HYPERTTS_GUI_DISPLAY"
else
    # a stale lock file from a killed X server prevents startup
    display_num="${HYPERTTS_GUI_DISPLAY#:}"
    if [ -e "/tmp/.X${display_num}-lock" ] && ! gui_port_in_use $((6000 + display_num)); then
        gui_log "removing stale X lock /tmp/.X${display_num}-lock"
        rm -f "/tmp/.X${display_num}-lock" "/tmp/.X11-unix/X${display_num}" 2>/dev/null || true
    fi
    gui_log "starting Xvfb on $HYPERTTS_GUI_DISPLAY ($HYPERTTS_GUI_SCREEN)"
    Xvfb "$HYPERTTS_GUI_DISPLAY" -screen 0 "$HYPERTTS_GUI_SCREEN" -ac -nolisten tcp \
        > "$HYPERTTS_GUI_LOG_DIR/xvfb.log" 2>&1 &
    echo $! > "$HYPERTTS_GUI_PID_DIR/xvfb.pid"
    sleep 1
fi

export DISPLAY="$HYPERTTS_GUI_DISPLAY"

# wait for the display to actually accept connections
for _ in $(seq 1 40); do
    if xdotool getdisplaygeometry > /dev/null 2>&1; then
        break
    fi
    sleep 0.25
done
if ! xdotool getdisplaygeometry > /dev/null 2>&1; then
    gui_log "ERROR: display $HYPERTTS_GUI_DISPLAY did not come up, see $HYPERTTS_GUI_LOG_DIR/xvfb.log"
    exit 1
fi

# a window manager is required for reliable modal dialog focus/stacking under Xvfb
if gui_pid_alive openbox; then
    gui_log "openbox already running"
else
    gui_log "starting openbox"
    openbox > "$HYPERTTS_GUI_LOG_DIR/openbox.log" 2>&1 &
    echo $! > "$HYPERTTS_GUI_PID_DIR/openbox.pid"
    sleep 0.5
fi

# vnc so a human can watch what the agent is doing
if gui_pid_alive x11vnc; then
    gui_log "x11vnc already running"
else
    gui_log "starting x11vnc on port $HYPERTTS_GUI_VNC_PORT"
    x11vnc -display "$HYPERTTS_GUI_DISPLAY" -nopw -forever -shared -localhost \
        -rfbport "$HYPERTTS_GUI_VNC_PORT" -quiet \
        > "$HYPERTTS_GUI_LOG_DIR/x11vnc.log" 2>&1 &
    echo $! > "$HYPERTTS_GUI_PID_DIR/x11vnc.pid"
fi

if gui_pid_alive novnc; then
    gui_log "novnc already running"
else
    gui_log "starting websockify/noVNC on port $HYPERTTS_GUI_NOVNC_PORT"
    websockify --web=/usr/share/novnc "$HYPERTTS_GUI_NOVNC_PORT" \
        "localhost:$HYPERTTS_GUI_VNC_PORT" \
        > "$HYPERTTS_GUI_LOG_DIR/novnc.log" 2>&1 &
    echo $! > "$HYPERTTS_GUI_PID_DIR/novnc.pid"
fi

gui_log "display ready: DISPLAY=$HYPERTTS_GUI_DISPLAY"
gui_log "watch it at http://localhost:$HYPERTTS_GUI_NOVNC_PORT/vnc.html"
