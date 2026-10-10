#!/bin/bash
# stop the automation Anki instance, leaving the virtual display running
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"

gui_kill_pidfile anki

# anki can leave QtWebEngine helper processes behind; only ever match processes
# whose command line references our isolated base folder so we never touch the
# developer's own Anki session
pids=$(pgrep -f "$HYPERTTS_GUI_ANKI_BASE" 2>/dev/null || true)
if [ -n "$pids" ]; then
    gui_log "killing leftover processes referencing $HYPERTTS_GUI_ANKI_BASE: $pids"
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids=$(pgrep -f "$HYPERTTS_GUI_ANKI_BASE" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        # shellcheck disable=SC2086
        kill -9 $pids 2>/dev/null || true
    fi
fi

gui_log "anki stopped"
