#!/bin/bash
# common environment for the HyperTTS GUI automation harness
# source this file, don't execute it

HYPERTTS_REPO_DIR="${HYPERTTS_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export HYPERTTS_REPO_DIR

# where all runtime state lives (anki base folder, logs, pid files, screenshots)
# deliberately outside the repo so pytest never tries to collect the anki addons
export HYPERTTS_GUI_WORKDIR="${HYPERTTS_GUI_WORKDIR:-/tmp/hypertts-gui-automation}"
export HYPERTTS_GUI_ANKI_BASE="$HYPERTTS_GUI_WORKDIR/anki_base"
export HYPERTTS_GUI_ANKI_PROFILE="${HYPERTTS_GUI_ANKI_PROFILE:-hypertts_test}"
export HYPERTTS_GUI_LOG_DIR="$HYPERTTS_GUI_WORKDIR/logs"
export HYPERTTS_GUI_PID_DIR="$HYPERTTS_GUI_WORKDIR/pids"
export HYPERTTS_GUI_ARTIFACT_DIR="$HYPERTTS_GUI_WORKDIR/artifacts"
export HYPERTTS_GUI_CACHE_DIR="$HYPERTTS_GUI_WORKDIR/cache"

# display / viewing
export HYPERTTS_GUI_DISPLAY="${HYPERTTS_GUI_DISPLAY:-:99}"
export HYPERTTS_GUI_SCREEN="${HYPERTTS_GUI_SCREEN:-1920x1080x24}"
export HYPERTTS_GUI_VNC_PORT="${HYPERTTS_GUI_VNC_PORT:-5999}"
export HYPERTTS_GUI_NOVNC_PORT="${HYPERTTS_GUI_NOVNC_PORT:-6099}"

# non-default ports so we can never accidentally drive the user's real Anki session,
# which would be listening on the AnkiConnect default of 8765
export HYPERTTS_GUI_ANKICONNECT_PORT="${HYPERTTS_GUI_ANKICONNECT_PORT:-8766}"
export HYPERTTS_GUI_PROBE_PORT="${HYPERTTS_GUI_PROBE_PORT:-8767}"

# python environment which has anki/aqt installed
export HYPERTTS_VENV="${HYPERTTS_VENV:-/home/luc/python-env/anki-hyper-tts-3.13}"

mkdir -p "$HYPERTTS_GUI_LOG_DIR" "$HYPERTTS_GUI_PID_DIR" "$HYPERTTS_GUI_ARTIFACT_DIR" "$HYPERTTS_GUI_CACHE_DIR"

gui_log() {
    echo "[gui-automation] $*"
}

# is the process referenced by a pid file alive ?
gui_pid_alive() {
    local pidfile="$HYPERTTS_GUI_PID_DIR/$1.pid"
    [ -f "$pidfile" ] || return 1
    local pid
    pid=$(cat "$pidfile")
    [ -n "$pid" ] || return 1
    kill -0 "$pid" 2>/dev/null
}

gui_kill_pidfile() {
    local name="$1"
    local pidfile="$HYPERTTS_GUI_PID_DIR/$name.pid"
    if [ -f "$pidfile" ]; then
        local pid
        pid=$(cat "$pidfile")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            gui_log "stopping $name (pid $pid)"
            kill "$pid" 2>/dev/null || true
            for _ in $(seq 1 40); do
                kill -0 "$pid" 2>/dev/null || break
                sleep 0.25
            done
            if kill -0 "$pid" 2>/dev/null; then
                gui_log "$name did not exit, sending SIGKILL"
                kill -9 "$pid" 2>/dev/null || true
            fi
        fi
        rm -f "$pidfile"
    fi
}

gui_wait_for_port() {
    local port="$1"
    local timeout="${2:-60}"
    local deadline=$((SECONDS + timeout))
    while [ $SECONDS -lt $deadline ]; do
        if (exec 3<>/dev/tcp/127.0.0.1/"$port") 2>/dev/null; then
            exec 3<&- 2>/dev/null || true
            return 0
        fi
        sleep 0.5
    done
    return 1
}

gui_port_in_use() {
    (exec 3<>/dev/tcp/127.0.0.1/"$1") 2>/dev/null && { exec 3<&- 2>/dev/null || true; return 0; }
    return 1
}
