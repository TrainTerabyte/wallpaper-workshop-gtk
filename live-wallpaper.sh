#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSHOP_DIR="$HOME/.local/share/Steam/steamapps/workshop/content/431960"
CONFIG_FILE="$HOME/.config/current_wallpaper"

killall -q linux-wallpaperengine 2>/dev/null

# Подгружаем сохранённые параметры (FPS, громкость, свойства сцены и геометрию)
WP_PROPS_ARGS=()
[ -f "$HOME/.config/wallpaper_env" ] && source "$HOME/.config/wallpaper_env"
FPS=${WP_FPS:-60}
VOL=${WP_VOLUME:-0}

# Определяем ID сцены (если конфига ещё нет — берём первую установленную из Workshop)
if [ -f "$CONFIG_FILE" ] && [ -s "$CONFIG_FILE" ]; then
    WALLPAPER_ID=$(cat "$CONFIG_FILE")
else
    WALLPAPER_ID=$(ls -1 "$WORKSHOP_DIR" 2>/dev/null | head -n 1)
    [ -z "$WALLPAPER_ID" ] && exit 1
    mkdir -p "$(dirname "$CONFIG_FILE")"
    echo "$WALLPAPER_ID" > "$CONFIG_FILE"
fi

# Автоопределение разрешения основного экрана при отсутствии WP_WIDTH / WP_HEIGHT
if [ -z "$WP_WIDTH" ] || [ -z "$WP_HEIGHT" ]; then
    RES=$(xrandr 2>/dev/null | awk '/ primary / {for(i=1;i<=NF;i++) if($i ~ /^[0-9]+x[0-9]+\+/) {split($i,a,"+"); print a[1]; exit}}')
    [ -z "$RES" ] && RES=$(xrandr 2>/dev/null | awk '/\*/ {print $1; exit}')
    W_WIDTH=${RES%x*}
    W_HEIGHT=${RES#*x}
    W_WIDTH=${W_WIDTH:-1920}
    W_HEIGHT=${W_HEIGHT:-1080}
else
    W_WIDTH=$WP_WIDTH
    W_HEIGHT=$WP_HEIGHT
fi
W_POS_X=${WP_POS_X:-0}
W_POS_Y=${WP_POS_Y:-0}

# Запуск движка с глобальными флагами и свойствами сцены
linux-wallpaperengine --silent --fps "$FPS" --volume "$VOL" "${WP_PROPS_ARGS[@]}" "$WALLPAPER_ID" >/dev/null 2>&1 &

# Ожидание окна рендера и привязка к рабочему столу
WID=""
for _ in {1..25}; do
    WID=$(xdotool search --name "^wallpaperengine$" 2>/dev/null | tail -n 1)
    [ -n "$WID" ] && break
    sleep 0.2
done

if [ -n "$WID" ]; then
    xprop -id "$WID" -f _MOTIF_WM_HINTS 32c -set _MOTIF_WM_HINTS "0x2, 0x0, 0x0, 0x0, 0x0"
    xprop -id "$WID" -f _NET_WM_WINDOW_TYPE 32a -set _NET_WM_WINDOW_TYPE _NET_WM_WINDOW_TYPE_DESKTOP
    xdotool windowsize "$WID" "$W_WIDTH" "$W_HEIGHT" windowmove "$WID" "$W_POS_X" "$W_POS_Y"
    wmctrl -i -r "$WID" -b add,below,sticky,skip_taskbar,skip_pager
fi

# Перезапуск сторожа автопаузы в полноэкранных играх
pkill -f "wallpaper-auto-pause.sh" 2>/dev/null
nohup "$SCRIPT_DIR/wallpaper-auto-pause.sh" >/dev/null 2>&1 &
