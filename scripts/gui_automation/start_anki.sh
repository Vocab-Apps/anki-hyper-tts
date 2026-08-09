#!/bin/bash
# start a full Anki instance on the virtual display, using an isolated base
# folder + profile, with HyperTTS, AnkiConnect and anki_gui_probe installed.
#
# idempotent: if Anki is already running and answering on the probe port, this
# is a no-op. Pass --restart to force a fresh instance (do this after editing
# HyperTTS python code).
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

RESTART=no
FRESH_COLLECTION=no
for arg in "$@"; do
    case "$arg" in
        --restart) RESTART=yes ;;
        --fresh) RESTART=yes; FRESH_COLLECTION=yes ;;
        *) gui_log "unknown argument: $arg"; exit 1 ;;
    esac
done

if [ "$RESTART" = yes ]; then
    "$SCRIPT_DIR/stop_anki.sh" || true
elif gui_pid_alive anki && gui_port_in_use "$HYPERTTS_GUI_PROBE_PORT"; then
    gui_log "anki already running (probe on port $HYPERTTS_GUI_PROBE_PORT)"
    exit 0
elif gui_pid_alive anki; then
    gui_log "anki process exists but probe port is not answering, restarting"
    "$SCRIPT_DIR/stop_anki.sh" || true
fi

"$SCRIPT_DIR/start_display.sh"

if [ "$FRESH_COLLECTION" = yes ] && [ -d "$HYPERTTS_GUI_ANKI_BASE" ]; then
    gui_log "removing base folder for a fresh collection: $HYPERTTS_GUI_ANKI_BASE"
    rm -rf "$HYPERTTS_GUI_ANKI_BASE"
fi

# refuse to start if something else already owns our ports (most likely a
# previous run which was not shut down cleanly)
for port_name in ANKICONNECT PROBE; do
    var="HYPERTTS_GUI_${port_name}_PORT"
    port="${!var}"
    if gui_port_in_use "$port"; then
        gui_log "ERROR: port $port ($port_name) is already in use, run scripts/gui_automation/teardown.sh"
        exit 1
    fi
done

# shellcheck disable=SC1091
source "$HYPERTTS_VENV/bin/activate"

# vocabai / cloudlanguagetools credentials for the QA backend, if available
HYPERTTS_SECRETS_FILE="${HYPERTTS_SECRETS_FILE:-/home/luc/code/secrets/hypertts/clt_tts_vocabai_qa.sh}"
if [ -f "$HYPERTTS_SECRETS_FILE" ]; then
    gui_log "sourcing secrets from $HYPERTTS_SECRETS_FILE"
    # shellcheck disable=SC1090
    source "$HYPERTTS_SECRETS_FILE"
fi

gui_log "preparing anki base $HYPERTTS_GUI_ANKI_BASE (profile $HYPERTTS_GUI_ANKI_PROFILE)"
python "$SCRIPT_DIR/setup_profile.py" \
    --base "$HYPERTTS_GUI_ANKI_BASE" \
    --profile "$HYPERTTS_GUI_ANKI_PROFILE" \
    --repo "$HYPERTTS_REPO_DIR" \
    --cache-dir "$HYPERTTS_GUI_CACHE_DIR" \
    --ankiconnect-port "$HYPERTTS_GUI_ANKICONNECT_PORT" \
    --secrets-file "$HYPERTTS_SECRETS_FILE"

export DISPLAY="$HYPERTTS_GUI_DISPLAY"
# no gpu on a virtual display
export LIBGL_ALWAYS_SOFTWARE=1
export QT_QUICK_BACKEND=software
export QTWEBENGINE_DISABLE_SANDBOX=1
export QTWEBENGINE_CHROMIUM_FLAGS="--no-sandbox --disable-gpu"
# expose the qt widget hierarchy over at-spi as a fallback inspection channel
export QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
export QT_ACCESSIBILITY=1
# hypertts debug logging to a file we can tail
export HYPER_TTS_DEBUG_LOGGING=file
export HYPER_TTS_DEBUG_LOGFILE="$HYPERTTS_GUI_LOG_DIR/hypertts.log"
export HYPERTTS_GUI_PROBE_PORT
# never let the automation instance sync
export ANKI_NOSYNC=1

: > "$HYPERTTS_GUI_LOG_DIR/anki.log"
gui_log "launching anki"
anki -b "$HYPERTTS_GUI_ANKI_BASE" -p "$HYPERTTS_GUI_ANKI_PROFILE" -l en \
    >> "$HYPERTTS_GUI_LOG_DIR/anki.log" 2>&1 &
echo $! > "$HYPERTTS_GUI_PID_DIR/anki.pid"

gui_log "waiting for anki_gui_probe on port $HYPERTTS_GUI_PROBE_PORT"
if ! gui_wait_for_port "$HYPERTTS_GUI_PROBE_PORT" 120; then
    gui_log "ERROR: probe did not come up. last lines of anki.log:"
    tail -40 "$HYPERTTS_GUI_LOG_DIR/anki.log"
    exit 1
fi

gui_log "waiting for AnkiConnect on port $HYPERTTS_GUI_ANKICONNECT_PORT"
if ! gui_wait_for_port "$HYPERTTS_GUI_ANKICONNECT_PORT" 60; then
    gui_log "WARNING: AnkiConnect did not come up. last lines of anki.log:"
    tail -40 "$HYPERTTS_GUI_LOG_DIR/anki.log"
fi

gui_log "anki is up"
gui_log "  probe:        http://127.0.0.1:$HYPERTTS_GUI_PROBE_PORT"
gui_log "  ankiconnect:  http://127.0.0.1:$HYPERTTS_GUI_ANKICONNECT_PORT"
gui_log "  watch:        http://localhost:$HYPERTTS_GUI_NOVNC_PORT/vnc.html"
gui_log "  anki log:     $HYPERTTS_GUI_LOG_DIR/anki.log"
gui_log "  hypertts log: $HYPERTTS_GUI_LOG_DIR/hypertts.log"
