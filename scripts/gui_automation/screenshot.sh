#!/bin/bash
# grab the whole virtual screen. Prefer the textual widget tree (gui_probe.py
# widget_tree) for assertions; use screenshots to check how things *look*.
#
# usage: screenshot.sh [name]
#   writes $HYPERTTS_GUI_WORKDIR/artifacts/<name>.png (default: screen.png)
set -euo pipefail

source "$(dirname "$(readlink -f "$0")")/common.sh"

name="${1:-screen}"
output="$HYPERTTS_GUI_ARTIFACT_DIR/${name}.png"

DISPLAY="$HYPERTTS_GUI_DISPLAY" import -window root "$output"
echo "$output"
