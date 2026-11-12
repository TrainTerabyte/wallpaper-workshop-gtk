#!/usr/bin/env bash
set -e

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local/share/wallpaper-workshop"
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"

echo "=== Установка Мастерской живых обоев (GUI для linux-wallpaperengine) ==="

MISSING=()
for cmd in python3 xdotool wmctrl xprop xrandr linux-wallpaperengine; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        MISSING+=("$cmd")
    fi
done

if ! python3 -c "import gi; gi.require_version('Gtk', '3.0'); from gi.repository import Gtk; from PIL import Image" 2>/dev/null; then
    MISSING+=("python3-gi / python3-pil")
fi

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "Внимание: не найдены следующие зависимости: ${MISSING[*]}"
    echo "Установите их перед запуском:"
    echo "  Ubuntu / Pop!_OS / Debian: sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 python3-pil xdotool wmctrl x11-utils"
    echo "  А также убедитесь, что бинарник linux-wallpaperengine доступен в PATH."
fi

mkdir -p "$INSTALL_DIR" "$BIN_DIR" "$APP_DIR"

cp "$SRC_DIR/wallpaper-selector.py" "$INSTALL_DIR/"
cp "$SRC_DIR/live-wallpaper.sh" "$INSTALL_DIR/"
cp "$SRC_DIR/wallpaper-playlist.sh" "$INSTALL_DIR/"
cp "$SRC_DIR/wallpaper-auto-pause.sh" "$INSTALL_DIR/"

chmod +x "$INSTALL_DIR/wallpaper-selector.py"          "$INSTALL_DIR/live-wallpaper.sh"          "$INSTALL_DIR/wallpaper-playlist.sh"          "$INSTALL_DIR/wallpaper-auto-pause.sh"

ln -sf "$INSTALL_DIR/wallpaper-selector.py" "$BIN_DIR/wallpaper-workshop"

cat << EOF > "$APP_DIR/wallpaper-workshop.desktop"
[Desktop Entry]
Type=Application
Name=Мастерская живых обоев
GenericName=Wallpaper Engine GUI
Comment=Графический менеджер живых обоев для linux-wallpaperengine
Exec=$INSTALL_DIR/wallpaper-selector.py
Icon=preferences-desktop-wallpaper
Terminal=false
Categories=Utility;GTK;
EOF

echo "Готово! Программа установлена в $INSTALL_DIR"
echo "Запуск из терминала: wallpaper-workshop (или через меню приложений «Мастерская живых обоев»)."
