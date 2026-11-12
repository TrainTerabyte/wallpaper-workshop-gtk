#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WAS_RUNNING=0

while true; do
    if pgrep -f "steamapps/common|\.exe|wine64-preloader" >/dev/null; then
        if pgrep -f "linux-wallpaperengine" >/dev/null; then
            killall -q linux-wallpaperengine
            WAS_RUNNING=1
        fi
    else
        if [ "$WAS_RUNNING" -eq 1 ]; then
            WAS_RUNNING=0
            "$SCRIPT_DIR/live-wallpaper.sh" >/dev/null 2>&1 &
        fi
    fi
    sleep 2
done
