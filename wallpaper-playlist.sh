#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

while true; do
    INFO=$(python3 - << 'PY'
import json, os, random

s_file = os.path.expanduser("~/.config/wallpaper_settings.json")
c_file = os.path.expanduser("~/.config/current_wallpaper")
if not os.path.exists(s_file):
    print("STOP")
    raise SystemExit

with open(s_file, "r", encoding="utf-8") as f:
    cfg = json.load(f)

pl = cfg.get("playlist", [])
if not cfg.get("playlist_enabled", False) or len(pl) < 2:
    print("STOP")
    raise SystemExit

interval = max(1, int(cfg.get("playlist_interval", 15))) * 60
order = cfg.get("playlist_order", "sequence")
cur = ""
if os.path.exists(c_file):
    with open(c_file, "r", encoding="utf-8") as f:
        cur = f.read().strip()

if order == "random":
    choices = [x for x in pl if x != cur] or pl
    nxt = random.choice(choices)
else:
    if cur in pl:
        nxt = pl[(pl.index(cur) + 1) % len(pl)]
    else:
        nxt = pl[0]

print(f"RUN|{interval}|{nxt}")
PY
)

    if [[ "$INFO" == "STOP" || -z "$INFO" ]]; then
        exit 0
    fi

    INTERVAL=$(echo "$INFO" | cut -d'|' -f2)

    ELAPSED=0
    while [ "$ELAPSED" -lt "$INTERVAL" ]; do
        sleep 5
        ELAPSED=$((ELAPSED + 5))
        ACTIVE=$(python3 -c 'import json,os; p=os.path.expanduser("~/.config/wallpaper_settings.json"); print("1" if os.path.exists(p) and json.load(open(p)).get("playlist_enabled") else "0")' 2>/dev/null)
        [ "$ACTIVE" != "1" ] && exit 0
    done

    # Если обои на паузе из-за запущенной игры — дожидаемся выхода
    if ! pgrep -f "linux-wallpaperengine" > /dev/null; then
        continue
    fi

    python3 - << 'PY'
import json, os, random, re, subprocess
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw

def detect_screen():
    try:
        out = subprocess.check_output(["xrandr"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            if " primary " in line:
                m = re.search(r"(\d+)x(\d+)\+", line)
                if m:
                    return int(m.group(1)), int(m.group(2))
        for line in out.splitlines():
            if "*" in line:
                m = re.search(r"(\d+)x(\d+)", line)
                if m:
                    return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1920, 1080

s_file = os.path.expanduser("~/.config/wallpaper_settings.json")
p_file = os.path.expanduser("~/.config/wallpaper_properties.json")
c_file = os.path.expanduser("~/.config/current_wallpaper")
e_file = os.path.expanduser("~/.config/wallpaper_env")
w_dir = os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960")
b_file = os.path.expanduser("~/.cache/wallpaper_backdrop.png")

with open(s_file, "r", encoding="utf-8") as f:
    cfg = json.load(f)

pl = cfg.get("playlist", [])
if not cfg.get("playlist_enabled", False) or len(pl) < 2:
    raise SystemExit

cur = open(c_file, encoding="utf-8").read().strip() if os.path.exists(c_file) else ""
if cfg.get("playlist_order", "sequence") == "random":
    choices = [x for x in pl if x != cur] or pl
    nxt = random.choice(choices)
else:
    nxt = pl[(pl.index(cur) + 1) % len(pl)] if cur in pl else pl[0]

all_props = json.load(open(p_file, encoding="utf-8")) if os.path.exists(p_file) else {}
active_props = all_props.get(nxt, {})
scaling = active_props.get("__scaling__", "fill")

sw, sh = detect_screen()
pw = int(round(sh * 9 / 16))
px = max(0, (sw - pw) // 2)

with open(c_file, "w", encoding="utf-8") as f:
    f.write(nxt)

if scaling == "portrait":
    scene_dir = os.path.join(w_dir, nxt)
    img_path = None
    pjson = os.path.join(scene_dir, "project.json")
    if os.path.exists(pjson):
        prev = json.load(open(pjson, encoding="utf-8", errors="ignore")).get("preview")
        if prev and os.path.exists(os.path.join(scene_dir, prev)):
            img_path = os.path.join(scene_dir, prev)
    if not img_path and os.path.isdir(scene_dir):
        for fn in os.listdir(scene_dir):
            if fn.lower().endswith(('.gif', '.jpg', '.jpeg', '.png', '.webp')):
                img_path = os.path.join(scene_dir, fn)
                break
    if img_path:
        with Image.open(img_path) as im:
            im.seek(0)
            fitted = ImageOps.fit(im.convert("RGB"), (sw, sh), Image.Resampling.BILINEAR)
            darkened = ImageEnhance.Brightness(fitted.filter(ImageFilter.GaussianBlur(radius=65))).enhance(0.48)
        shadow = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rectangle([px, 0, px + pw, sh], fill=(0, 0, 0, 230))
        bg = darkened.convert("RGBA")
        bg.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(radius=50)))
        bg.convert("RGB").save(b_file, "PNG")
        uri = f"file://{b_file}"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-options", "zoom"], check=False)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], check=False)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=False)

with open(e_file, "w", encoding="utf-8") as f:
    f.write(f"export WP_FPS={cfg.get('fps', 60)}\n")
    f.write(f"export WP_VOLUME={cfg.get('volume', 0)}\n")
    if scaling == "portrait":
        f.write(f"export WP_WIDTH={pw}\nexport WP_HEIGHT={sh}\nexport WP_POS_X={px}\nexport WP_POS_Y=0\n")
        eng_scale = "fill"
    else:
        f.write(f"export WP_WIDTH={sw}\nexport WP_HEIGHT={sh}\nexport WP_POS_X=0\nexport WP_POS_Y=0\n")
        eng_scale = "fill" if scaling == "fit" else scaling
    f.write("WP_PROPS_ARGS=(\n")
    f.write(f'  --scaling "{eng_scale}"\n')
    for k, v in active_props.items():
        if k == "__scaling__":
            continue
        val_str = ("true" if v else "false") if isinstance(v, bool) else str(v)
        f.write(f'  --set-property "{k}={val_str}"\n')
    f.write(")\n")
PY

    "$SCRIPT_DIR/live-wallpaper.sh" &
done
