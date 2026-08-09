#!/bin/bash
# shut everything down: anki, noVNC, x11vnc, openbox, Xvfb.
# ALWAYS run this when an agentic GUI session is finished.
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

"$SCRIPT_DIR/stop_anki.sh" || true

gui_kill_pidfile novnc
gui_kill_pidfile x11vnc
gui_kill_pidfile openbox
gui_kill_pidfile xvfb

# clean up the X lock so the next run can reuse the same display number
display_num="${HYPERTTS_GUI_DISPLAY#:}"
rm -f "/tmp/.X${display_num}-lock" "/tmp/.X11-unix/X${display_num}" 2>/dev/null || true

gui_log "teardown complete"
# note: only ever report/kill processes tied to our display or our base folder.
# the developer's own openbox / vnc / anki must be left alone.
leftover=$(pgrep -a -f "Xvfb $HYPERTTS_GUI_DISPLAY|$HYPERTTS_GUI_ANKI_BASE" \
    | grep -v "teardown.sh" || true)
if [ -n "$leftover" ]; then
    gui_log "WARNING: leftover processes:"
    echo "$leftover"
else
    gui_log "no leftover processes"
fi
