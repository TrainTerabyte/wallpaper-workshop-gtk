#!/usr/bin/env python3
import os
import re
import json
import subprocess
from PIL import Image, ImageOps, ImageFilter, ImageEnhance, ImageDraw
import gi

gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk, Pango

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSHOP_DIR = os.path.expanduser("~/.local/share/Steam/steamapps/workshop/content/431960")
CONFIG_FILE = os.path.expanduser("~/.config/current_wallpaper")
SETTINGS_FILE = os.path.expanduser("~/.config/wallpaper_settings.json")
PROPS_CACHE_FILE = os.path.expanduser("~/.config/wallpaper_properties.json")
ENV_FILE = os.path.expanduser("~/.config/wallpaper_env")
RUN_SCRIPT = os.path.join(SCRIPT_DIR, "live-wallpaper.sh")
PLAYLIST_SCRIPT = os.path.join(SCRIPT_DIR, "wallpaper-playlist.sh")
THUMB_CACHE_DIR = os.path.expanduser("~/.cache/wallpaper_thumbs")
BACKDROP_FILE = os.path.expanduser("~/.cache/wallpaper_backdrop.png")

os.makedirs(THUMB_CACHE_DIR, exist_ok=True)
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

SIZES = {
    "small": (160, 100),
    "medium": (250, 155),
    "large": (370, 230)
}

PAGE_SIZES = {
    "small": 40,
    "medium": 24,
    "large": 12
}

DEFAULT_SETTINGS = {
    "fps": 60,
    "volume": 0,
    "sort_by": "newest",
    "size": "medium",
    "favorites": [],
    "hidden": [],
    "playlist": [],
    "playlist_enabled": False,
    "playlist_interval": 15,
    "playlist_order": "sequence",
    "filters": {}
}

TAG_DEFINITIONS = [
    ("abstract", "Абстракция", ["abstract"]),
    ("animal", "Животные", ["animal", "animals"]),
    ("anime", "Аниме", ["anime"]),
    ("cartoon", "Мультфильм", ["cartoon"]),
    ("cgi", "Комп. графика", ["cgi"]),
    ("cyberpunk", "Киберпанк", ["cyberpunk"]),
    ("fantasy", "Фантастика", ["fantasy"]),
    ("game", "Игра", ["game", "games"]),
    ("girls", "Девушки", ["girls", "girl"]),
    ("guys", "Парни", ["guys", "guy"]),
    ("landscape", "Пейзаж", ["landscape"]),
    ("medieval", "Средневековье", ["medieval"]),
    ("memes", "Мемы", ["memes", "meme"]),
    ("mmd", "MikuMikuDance (анимация)", ["mmd", "mikumikudance"]),
    ("music", "Музыка", ["music"]),
    ("nature", "Природа", ["nature"]),
    ("pixelart", "Пиксель-арт", ["pixel art", "pixelart"]),
    ("relaxing", "Расслабляющий", ["relaxing"]),
    ("retro", "Ретро", ["retro"]),
    ("scifi", "Научная фантастика", ["sci-fi", "scifi", "science fiction"]),
    ("sports", "Спорт", ["sports", "sport"]),
    ("technology", "Технологии", ["technology", "tech"]),
    ("television", "Телевидение", ["television", "tv"]),
    ("vehicle", "Транспорт", ["vehicle", "vehicles", "car", "cars"]),
    ("unspecified", "Неопределенный жанр", ["unspecified"])
]

def get_primary_screen_size():
    """Автоматически определяет разрешение основного монитора пользователя."""
    try:
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_primary_monitor() or display.get_monitor(0)
            if monitor:
                geo = monitor.get_geometry()
                if geo.width > 0 and geo.height > 0:
                    return int(geo.width), int(geo.height)
        screen = Gdk.Screen.get_default()
        if screen and screen.get_width() > 0 and screen.get_height() > 0:
            return int(screen.get_width()), int(screen.get_height())
    except Exception:
        pass
    return 1920, 1080

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return {**DEFAULT_SETTINGS, **json.load(f)}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings_data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def load_all_custom_properties():
    if os.path.exists(PROPS_CACHE_FILE):
        try:
            with open(PROPS_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_all_custom_properties(all_props):
    try:
        with open(PROPS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(all_props, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def generate_blurred_backdrop(img_path):
    """Создаёт размытую подложку под разрешение текущего монитора с тенью для портретных сцен 9:16."""
    if not img_path or not os.path.exists(img_path):
        return
    sw, sh = get_primary_screen_size()
    pw = int(round(sh * 9 / 16))
    px = max(0, (sw - pw) // 2)
    try:
        with Image.open(img_path) as im:
            im.seek(0)
            base = im.convert("RGB")
            fitted = ImageOps.fit(base, (sw, sh), Image.Resampling.BILINEAR)
            blurred = fitted.filter(ImageFilter.GaussianBlur(radius=65))
            darkened = ImageEnhance.Brightness(blurred).enhance(0.48)

        shadow_layer = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
        draw = ImageDraw.Draw(shadow_layer)
        draw.rectangle([px, 0, px + pw, sh], fill=(0, 0, 0, 230))
        shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=50))

        backdrop_rgba = darkened.convert("RGBA")
        backdrop_rgba.alpha_composite(shadow_blurred)
        final_bg = backdrop_rgba.convert("RGB")
        final_bg.save(BACKDROP_FILE, "PNG")

        uri = f"file://{BACKDROP_FILE}"
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-options", "zoom"], check=False)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri], check=False)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", uri], check=False)
    except Exception as e:
        print("Backdrop generation error:", e)

def export_env(settings, active_props=None):
    active_props = active_props or {}
    scaling = active_props.get("__scaling__", "fill")
    sw, sh = get_primary_screen_size()
    pw = int(round(sh * 9 / 16))
    px = max(0, (sw - pw) // 2)
    try:
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(f"export WP_FPS={settings.get('fps', 60)}\n")
            f.write(f"export WP_VOLUME={settings.get('volume', 0)}\n")

            if scaling == "portrait":
                f.write(f"export WP_WIDTH={pw}\n")
                f.write(f"export WP_HEIGHT={sh}\n")
                f.write(f"export WP_POS_X={px}\n")
                f.write("export WP_POS_Y=0\n")
                engine_scaling = "fill"
            else:
                f.write(f"export WP_WIDTH={sw}\n")
                f.write(f"export WP_HEIGHT={sh}\n")
                f.write("export WP_POS_X=0\n")
                f.write("export WP_POS_Y=0\n")
                engine_scaling = "fill" if scaling == "fit" else scaling

            f.write("WP_PROPS_ARGS=(\n")
            f.write(f'  --scaling "{engine_scaling}"\n')
            for k, v in active_props.items():
                if k == "__scaling__":
                    continue
                if isinstance(v, bool):
                    val_str = "true" if v else "false"
                else:
                    val_str = str(v)
                f.write(f'  --set-property "{k}={val_str}"\n')
            f.write(")\n")
    except Exception:
        pass

class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent, current_settings):
        super().__init__(title="Настройки параметров", transient_for=parent, flags=0)
        self.add_button("Отмена", Gtk.ResponseType.CANCEL)
        self.add_button("Сохранить", Gtk.ResponseType.OK)
        self.set_default_size(320, 220)
        self.set_modal(True)

        content = self.get_content_area()
        grid = Gtk.Grid(column_spacing=12, row_spacing=12, margin=15)
        content.add(grid)

        lbl_sort = Gtk.Label(label="Сортировка:", halign=Gtk.Align.START)
        self.combo_sort = Gtk.ComboBoxText()
        self.combo_sort.append("newest", "Сначала новые (свежие)")
        self.combo_sort.append("name", "По названию (А-Я)")
        self.combo_sort.append("id", "По номеру (ID)")
        self.combo_sort.set_active_id(current_settings.get("sort_by", "newest"))
        grid.attach(lbl_sort, 0, 0, 1, 1)
        grid.attach(self.combo_sort, 1, 0, 1, 1)

        lbl_fps = Gtk.Label(label="Частота кадров (FPS):", halign=Gtk.Align.START)
        self.combo_fps = Gtk.ComboBoxText()
        for f in ["30", "60", "90", "120", "144"]:
            self.combo_fps.append(f, f"{f} FPS")
        self.combo_fps.set_active_id(str(current_settings.get("fps", 60)))
        grid.attach(lbl_fps, 0, 1, 1, 1)
        grid.attach(self.combo_fps, 1, 1, 1, 1)

        lbl_vol = Gtk.Label(label="Громкость обоев:", halign=Gtk.Align.START)
        self.scale_vol = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
        self.scale_vol.set_value(current_settings.get("volume", 0))
        self.scale_vol.set_hexpand(True)
        self.scale_vol.set_digits(0)
        grid.attach(lbl_vol, 0, 2, 1, 1)
        grid.attach(self.scale_vol, 1, 2, 1, 1)

        self.show_all()

    def get_values(self):
        return {
            "sort_by": self.combo_sort.get_active_id(),
            "fps": int(self.combo_fps.get_active_id() or 60),
            "volume": int(self.scale_vol.get_value())
        }

class PlaylistSettingsDialog(Gtk.Dialog):
    def __init__(self, parent, current_settings):
        super().__init__(title="Настройки плейлиста", transient_for=parent, flags=0)
        self.add_button("Отмена", Gtk.ResponseType.CANCEL)
        self.add_button("Сохранить", Gtk.ResponseType.OK)
        self.set_default_size(340, 180)
        self.set_modal(True)

        grid = Gtk.Grid(column_spacing=12, row_spacing=12, margin=15)
        self.get_content_area().add(grid)

        lbl_int = Gtk.Label(label="Менять обои каждые:", halign=Gtk.Align.START)
        self.combo_int = Gtk.ComboBoxText()
        for mins, label in [
            ("1", "1 минуту"),
            ("5", "5 минут"),
            ("10", "10 минут"),
            ("15", "15 минут"),
            ("30", "30 минут"),
            ("60", "1 час")
        ]:
            self.combo_int.append(mins, label)
        self.combo_int.set_active_id(str(current_settings.get("playlist_interval", 15)))
        grid.attach(lbl_int, 0, 0, 1, 1)
        grid.attach(self.combo_int, 1, 0, 1, 1)

        lbl_ord = Gtk.Label(label="Порядок воспроизведения:", halign=Gtk.Align.START)
        self.combo_ord = Gtk.ComboBoxText()
        self.combo_ord.append("sequence", "По порядку")
        self.combo_ord.append("random", "Случайно")
        self.combo_ord.set_active_id(current_settings.get("playlist_order", "sequence"))
        grid.attach(lbl_ord, 0, 1, 1, 1)
        grid.attach(self.combo_ord, 1, 1, 1, 1)

        self.show_all()

    def get_values(self):
        return {
            "playlist_interval": int(self.combo_int.get_active_id() or 15),
            "playlist_order": self.combo_ord.get_active_id() or "sequence"
        }

class WallpaperGallery(Gtk.Window):
    def __init__(self):
        super().__init__(title="Мастерская живых обоев")
        _init_cfg = load_settings()
        sw, sh = get_primary_screen_size()
        _w = min(_init_cfg.get("win_width", min(1440, int(sw * 0.85))), sw)
        _h = min(_init_cfg.get("win_height", min(850, int(sh * 0.85))), sh)
        self.set_default_size(_w, _h)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.connect("delete-event", self.on_window_close)

        settings = Gtk.Settings.get_default()
        if settings:
            settings.set_property("gtk-application-prefer-dark-theme", True)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
        iconview:selected, iconview.view:selected {
            background-color: #1b6acb;
            border: 2px solid #62a0ea;
            border-radius: 6px;
        }
        .sidebar-panel {
            background-color: #262626;
            border-right: 1px solid #383838;
            padding: 8px;
        }
        .right-panel {
            background-color: #262626;
            border-left: 1px solid #383838;
            padding: 10px;
        }
        .inspector-title {
            font-size: 14px;
            font-weight: bold;
            color: #ffffff;
        }
        .inspector-meta {
            font-size: 11px;
            color: #aaaaaa;
        }
        .reset-btn {
            background-image: none;
            background-color: #5275d6;
            color: #ffffff;
            font-weight: bold;
            border-radius: 4px;
        }
        .link-btn {
            padding: 0px 4px;
            min-height: 20px;
            color: #62a0ea;
        }
        .playlist-panel {
            background-color: #222222;
            border: 1px solid #383838;
            border-radius: 6px;
            padding: 6px 8px;
        }
        .playlist-del-btn {
            padding: 0px 4px;
            min-height: 16px;
            min-width: 16px;
            font-size: 10px;
        }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.app_settings = load_settings()
        self.all_custom_props = load_all_custom_properties()
        self.current_size_name = self.app_settings.get("size", "medium")
        self.search_query = ""
        self.items_data = []
        self.filtered_items = []
        self.current_page = 0
        self.page_size = PAGE_SIZES.get(self.current_size_name, 24)
        self.raw_props_cache = {}
        self.img_paths_map = {}
        self.meta_map = {}
        self.updating_filters = False

        saved_filters = self.app_settings.get("filters", {})
        saved_type = saved_filters.get("type", {})
        saved_rating = saved_filters.get("rating", {})
        saved_tags = saved_filters.get("tags", {})
        saved_res = saved_filters.get("res", {})

        self.type_checks = {}
        self.rating_checks = {}
        self.res_checks = {}
        self.tag_checks = {}

        self.connect("key-press-event", self.on_key_press_event)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        vbox.set_margin_top(10)
        vbox.set_margin_bottom(10)
        vbox.set_margin_start(10)
        vbox.set_margin_end(10)
        self.add(vbox)

        # Верхняя панель
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(top_box, False, False, 0)

        self.btn_sidebar = Gtk.ToggleButton(label="☰")
        self.btn_sidebar.set_tooltip_text("Показать или скрыть панель фильтров (F9)")
        self.btn_sidebar.set_active(self.app_settings.get("show_sidebar", True))
        self.btn_sidebar.connect("toggled", self.on_sidebar_toggled)
        top_box.pack_start(self.btn_sidebar, False, False, 0)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Быстрый поиск сцены...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        top_box.pack_start(self.search_entry, True, True, 0)

        btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        btn_refresh.set_tooltip_text("Обновить список из мастерской (F5)")
        btn_refresh.connect("clicked", lambda b: self.refresh_gallery())
        top_box.pack_start(btn_refresh, False, False, 0)

        size_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        size_box.get_style_context().add_class("linked")

        self.btn_s = Gtk.RadioButton.new_with_label_from_widget(None, "Мелкий")
        self.btn_m = Gtk.RadioButton.new_with_label_from_widget(self.btn_s, "Средний")
        self.btn_l = Gtk.RadioButton.new_with_label_from_widget(self.btn_s, "Крупный")

        for b in (self.btn_s, self.btn_m, self.btn_l):
            b.set_mode(False)
            size_box.pack_start(b, False, False, 0)

        self.btn_s.connect("toggled", lambda b: self.on_size_toggled("small") if b.get_active() else None)
        self.btn_m.connect("toggled", lambda b: self.on_size_toggled("medium") if b.get_active() else None)
        self.btn_l.connect("toggled", lambda b: self.on_size_toggled("large") if b.get_active() else None)
        top_box.pack_start(size_box, False, False, 0)

        btn_settings = Gtk.Button.new_from_icon_name("emblem-system-symbolic", Gtk.IconSize.BUTTON)
        btn_settings.set_tooltip_text("Настройки рендера и сортировки")
        btn_settings.connect("clicked", self.on_settings_clicked)
        top_box.pack_start(btn_settings, False, False, 0)

        # Центральная область: Окно фильтров + Галерея + Инспектор
        mid_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(mid_hbox, True, True, 0)

        self.filter_win = Gtk.Window(title="Фильтры")
        self.filter_win.set_transient_for(self)
        self.filter_win.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.filter_win.set_default_size(255, 760)
        self.filter_win.connect("delete-event", self.on_filter_win_close)

        self.sidebar_scroll = Gtk.ScrolledWindow()
        self.sidebar_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.sidebar_scroll.get_style_context().add_class("sidebar-panel")
        self.filter_win.add(self.sidebar_scroll)

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        sidebar_box.set_margin_top(6)
        sidebar_box.set_margin_bottom(6)
        sidebar_box.set_margin_start(8)
        sidebar_box.set_margin_end(8)
        self.sidebar_scroll.add(sidebar_box)

        btn_reset = Gtk.Button(label="↻ Сбросить фильтры")
        btn_reset.get_style_context().add_class("reset-btn")
        btn_reset.connect("clicked", self.on_reset_filters)
        sidebar_box.pack_start(btn_reset, False, False, 0)

        self.chk_only_fav = Gtk.CheckButton(label="★ Только избранное")
        self.chk_only_fav.set_active(saved_filters.get("only_fav", False))
        self.chk_only_fav.connect("toggled", self.on_filter_toggled)
        sidebar_box.pack_start(self.chk_only_fav, False, False, 2)

        self.chk_show_hidden = Gtk.CheckButton(label="👁 Показать скрытые")
        self.chk_show_hidden.set_tooltip_text("Показывать скрытые сцены в галерее")
        self.chk_show_hidden.set_active(saved_filters.get("show_hidden", False))
        self.chk_show_hidden.connect("toggled", self.on_filter_toggled)
        sidebar_box.pack_start(self.chk_show_hidden, False, False, 2)

        # Секция 1: Тип
        exp_type = Gtk.Expander(label="Тип")
        exp_type.set_expanded(True)
        type_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        type_box.set_margin_start(8)
        type_box.set_margin_top(4)

        for key, label in [
            ("scene", "Сцена"),
            ("video", "Видео"),
            ("web", "Веб"),
            ("application", "Приложение")
        ]:
            chk = Gtk.CheckButton(label=label)
            chk.set_active(saved_type.get(key, True))
            chk.connect("toggled", self.on_filter_toggled)
            type_box.pack_start(chk, False, False, 0)
            self.type_checks[key] = chk

        exp_type.add(type_box)
        sidebar_box.pack_start(exp_type, False, False, 0)
        sidebar_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Секция 2: Возрастной рейтинг
        exp_rating = Gtk.Expander(label="Возрастной рейтинг")
        exp_rating.set_expanded(True)
        rating_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        rating_box.set_margin_start(8)
        rating_box.set_margin_top(4)

        for key, label in [
            ("everyone", "0+ (для всех возрастов)"),
            ("questionable", "12+ (с ограничениями)"),
            ("mature", "18+ (для взрослых)")
        ]:
            chk = Gtk.CheckButton(label=label)
            chk.set_active(saved_rating.get(key, True))
            chk.connect("toggled", self.on_filter_toggled)
            rating_box.pack_start(chk, False, False, 0)
            self.rating_checks[key] = chk

        exp_rating.add(rating_box)
        sidebar_box.pack_start(exp_rating, False, False, 0)
        sidebar_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Секция 3: Метки
        exp_tags = Gtk.Expander(label="Метки")
        exp_tags.set_expanded(True)
        tags_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        tags_box.set_margin_start(8)
        tags_box.set_margin_top(4)

        quick_tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_all_tags = Gtk.Button(label="Все")
        btn_all_tags.set_relief(Gtk.ReliefStyle.NONE)
        btn_all_tags.get_style_context().add_class("link-btn")
        btn_all_tags.connect("clicked", lambda b: self.set_all_tag_checks(True))

        btn_none_tags = Gtk.Button(label="Ничего")
        btn_none_tags.set_relief(Gtk.ReliefStyle.NONE)
        btn_none_tags.get_style_context().add_class("link-btn")
        btn_none_tags.connect("clicked", lambda b: self.set_all_tag_checks(False))

        quick_tag_box.pack_start(btn_all_tags, False, False, 0)
        quick_tag_box.pack_start(btn_none_tags, False, False, 0)
        tags_box.pack_start(quick_tag_box, False, False, 0)

        for key, label, _ in TAG_DEFINITIONS:
            chk = Gtk.CheckButton(label=label)
            chk.set_active(saved_tags.get(key, True))
            chk.connect("toggled", self.on_filter_toggled)
            tags_box.pack_start(chk, False, False, 0)
            self.tag_checks[key] = chk

        exp_tags.add(tags_box)
        sidebar_box.pack_start(exp_tags, False, False, 0)
        sidebar_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 2)

        # Секция 4: Разрешение экрана
        exp_res = Gtk.Expander(label="Разрешение экрана")
        exp_res.set_expanded(True)
        res_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        res_box.set_margin_start(8)
        res_box.set_margin_top(4)

        lbl_wide = Gtk.Label(label="Широкий и вертикальный экран", halign=Gtk.Align.START)
        res_box.pack_start(lbl_wide, False, False, 2)

        quick_res_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_all_res = Gtk.Button(label="Все")
        btn_all_res.set_relief(Gtk.ReliefStyle.NONE)
        btn_all_res.get_style_context().add_class("link-btn")
        btn_all_res.connect("clicked", lambda b: self.set_all_res_checks(True))

        btn_none_res = Gtk.Button(label="Ничего")
        btn_none_res.set_relief(Gtk.ReliefStyle.NONE)
        btn_none_res.get_style_context().add_class("link-btn")
        btn_none_res.connect("clicked", lambda b: self.set_all_res_checks(False))

        quick_res_box.pack_start(btn_all_res, False, False, 0)
        quick_res_box.pack_start(btn_none_res, False, False, 0)
        res_box.pack_start(quick_res_box, False, False, 0)

        for key, label in [
            ("standard", "Стандартное разрешение"),
            ("720p", "1280 x 720"),
            ("768p", "1366 x 768"),
            ("1080p", "1920 x 1080 - Full HD"),
            ("1440p", "2560 x 1440"),
            ("4k", "3840 x 2160 - 4K"),
            ("portrait", "Портретные (9:16)")
        ]:
            chk = Gtk.CheckButton(label=label)
            chk.set_active(saved_res.get(key, True))
            chk.connect("toggled", self.on_filter_toggled)
            res_box.pack_start(chk, False, False, 0)
            self.res_checks[key] = chk

        exp_res.add(res_box)
        sidebar_box.pack_start(exp_res, False, False, 0)

        # Центральная колонка: галерея + панель страниц
        center_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        mid_hbox.pack_start(center_vbox, True, True, 0)

        self._last_grid_sig = None
        self._layout_idle_id = 0
        self.gallery_scroll = Gtk.ScrolledWindow()
        self.gallery_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.gallery_scroll.set_propagate_natural_width(False)
        self.gallery_scroll.set_min_content_width(200)
        self.gallery_scroll.connect("size-allocate", self.on_gallery_size_allocate)
        center_vbox.pack_start(self.gallery_scroll, True, True, 0)

        self.model = Gtk.ListStore(str, str, GdkPixbuf.Pixbuf)
        self.iconview = Gtk.IconView(model=self.model)
        self.iconview.set_pixbuf_column(2)
        self.iconview.set_tooltip_column(1)
        self.iconview.set_column_spacing(6)
        self.iconview.set_row_spacing(6)
        self.iconview.set_item_padding(4)
        self.iconview.set_margin(4)
        self.iconview.connect("item-activated", self.on_item_activated)
        self.iconview.connect("selection-changed", self.on_selection_changed)
        self.gallery_scroll.add(self.iconview)

        # Панель переключения страниц
        page_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        page_bar.set_halign(Gtk.Align.CENTER)
        self.btn_prev_page = Gtk.Button(label="◀ Назад")
        self.btn_prev_page.connect("clicked", lambda b: self.change_page(-1))
        self.lbl_page_info = Gtk.Label(label="Страница 1 из 1")
        self.btn_next_page = Gtk.Button(label="Вперёд ▶")
        self.btn_next_page.connect("clicked", lambda b: self.change_page(1))

        page_bar.pack_start(self.btn_prev_page, False, False, 0)
        page_bar.pack_start(self.lbl_page_info, False, False, 0)
        page_bar.pack_start(self.btn_next_page, False, False, 0)
        center_vbox.pack_start(page_bar, False, False, 0)

        # Правая панель инспектора
        self.insp_wp_id = None
        self.insp_widget_map = {}

        self.right_scroll = Gtk.ScrolledWindow()
        self.right_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.right_scroll.set_size_request(315, -1)
        self.right_scroll.set_propagate_natural_width(False)
        self.right_scroll.set_min_content_width(315)
        self.right_scroll.get_style_context().add_class("right-panel")
        mid_hbox.pack_start(self.right_scroll, False, False, 0)

        self.right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.right_box.set_margin_top(4)
        self.right_box.set_margin_bottom(8)
        self.right_box.set_margin_start(6)
        self.right_box.set_margin_end(6)
        self.right_scroll.add(self.right_box)

        self.insp_image = Gtk.Image()
        self.right_box.pack_start(self.insp_image, False, False, 0)

        self.insp_title = Gtk.Label(label="Нет выбранной сцены")
        self.insp_title.set_line_wrap(True)
        self.insp_title.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.insp_title.set_max_width_chars(32)
        self.insp_title.set_justify(Gtk.Justification.CENTER)
        self.insp_title.get_style_context().add_class("inspector-title")
        self.right_box.pack_start(self.insp_title, False, False, 2)

        self.insp_meta = Gtk.Label(label="")
        self.insp_meta.set_line_wrap(True)
        self.insp_meta.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.insp_meta.set_max_width_chars(36)
        self.insp_meta.set_justify(Gtk.Justification.CENTER)
        self.insp_meta.get_style_context().add_class("inspector-meta")
        self.right_box.pack_start(self.insp_meta, False, False, 0)

        fav_hide_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_insp_fav = Gtk.Button(label="☆ В избранное")
        self.btn_insp_fav.set_tooltip_text("Добавить или убрать из избранного (F)")
        self.btn_insp_fav.connect("clicked", self.on_toggle_favorite_clicked)

        self.btn_insp_hide = Gtk.Button(label="🚫 Скрыть")
        self.btn_insp_hide.set_tooltip_text("Скрыть или вернуть сцену (Delete)")
        self.btn_insp_hide.connect("clicked", self.on_toggle_hidden_clicked)

        fav_hide_box.pack_start(self.btn_insp_fav, True, True, 0)
        fav_hide_box.pack_start(self.btn_insp_hide, False, False, 0)
        self.right_box.pack_start(fav_hide_box, False, False, 2)

        self.right_box.pack_start(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL), False, False, 4)

        lbl_props_hdr = Gtk.Label(label="Свойства", halign=Gtk.Align.START)
        lbl_props_hdr.get_style_context().add_class("inspector-title")
        self.right_box.pack_start(lbl_props_hdr, False, False, 0)

        self.insp_props_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.right_box.pack_start(self.insp_props_box, False, False, 2)

        insp_btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        btn_insp_apply = Gtk.Button(label="Применить свойства")
        btn_insp_apply.get_style_context().add_class("suggested-action")
        btn_insp_apply.connect("clicked", self.on_insp_apply_clicked)

        btn_insp_reset = Gtk.Button(label="↻ Сбросить")
        btn_insp_reset.connect("clicked", self.on_insp_reset_clicked)

        insp_btns.pack_start(btn_insp_apply, True, True, 0)
        insp_btns.pack_start(btn_insp_reset, False, False, 0)
        self.right_box.pack_start(insp_btns, False, False, 6)

        self.preload_data()

        if self.current_size_name == "small":
            self.btn_s.set_active(True)
        elif self.current_size_name == "large":
            self.btn_l.set_active(True)
        else:
            self.btn_m.set_active(True)

        self.apply_filters(reset_page=True, render=False)
        self.select_initial_active_wallpaper()
        if self.btn_sidebar.get_active():
            GLib.idle_add(self.position_and_show_filters)

        # Панель плейлиста
        pl_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        pl_frame.get_style_context().add_class("playlist-panel")
        vbox.pack_start(pl_frame, False, False, 0)

        pl_top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pl_frame.pack_start(pl_top, False, False, 0)

        self.lbl_pl_title = Gtk.Label(label="Плейлист (0)", halign=Gtk.Align.START)
        self.lbl_pl_title.get_style_context().add_class("inspector-title")
        pl_top.pack_start(self.lbl_pl_title, False, False, 0)

        self.btn_pl_add = Gtk.Button(label="+ Добавить выбранную")
        self.btn_pl_add.connect("clicked", self.on_playlist_add_clicked)
        pl_top.pack_start(self.btn_pl_add, False, False, 0)

        btn_pl_cfg = Gtk.Button(label="⚙ Настроить")
        btn_pl_cfg.connect("clicked", self.on_playlist_settings_clicked)
        pl_top.pack_start(btn_pl_cfg, False, False, 0)

        btn_pl_clear = Gtk.Button(label="🗑 Очистить")
        btn_pl_clear.connect("clicked", self.on_playlist_clear_clicked)
        pl_top.pack_start(btn_pl_clear, False, False, 0)

        self.btn_pl_toggle = Gtk.ToggleButton(label="▶ Запустить плейлист")
        self.btn_pl_toggle.set_active(self.app_settings.get("playlist_enabled", False))
        self.btn_pl_toggle.connect("toggled", self.on_playlist_toggled)
        pl_top.pack_end(self.btn_pl_toggle, False, False, 0)

        self.pl_scroll = Gtk.ScrolledWindow()
        self.pl_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.pl_scroll.set_min_content_height(66)
        pl_frame.pack_start(self.pl_scroll, False, False, 0)

        self.pl_strip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.pl_scroll.add(self.pl_strip_box)
        self.render_playlist_strip()
        self.update_playlist_add_button()

        # Нижняя панель
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        vbox.pack_start(hbox, False, False, 0)

        btn_close = Gtk.Button(label="Закрыть")
        btn_close.connect("clicked", lambda b: Gtk.main_quit())
        hbox.pack_end(btn_close, False, False, 0)

        btn_apply = Gtk.Button(label="Применить")
        btn_apply.get_style_context().add_class("suggested-action")
        btn_apply.connect("clicked", self.on_apply_clicked)
        hbox.pack_end(btn_apply, False, False, 0)

    def save_filter_state(self):
        self.app_settings["filters"] = {
            "only_fav": self.chk_only_fav.get_active(),
            "show_hidden": self.chk_show_hidden.get_active(),
            "type": {k: chk.get_active() for k, chk in self.type_checks.items()},
            "rating": {k: chk.get_active() for k, chk in self.rating_checks.items()},
            "tags": {k: chk.get_active() for k, chk in self.tag_checks.items()},
            "res": {k: chk.get_active() for k, chk in self.res_checks.items()}
        }
        save_settings(self.app_settings)

    def on_filter_toggled(self, widget):
        if not self.updating_filters:
            self.save_filter_state()
            self.apply_filters(reset_page=True)

    def set_all_tag_checks(self, state):
        self.updating_filters = True
        for chk in self.tag_checks.values():
            chk.set_active(state)
        self.updating_filters = False
        self.save_filter_state()
        self.apply_filters(reset_page=True)

    def set_all_res_checks(self, state):
        self.updating_filters = True
        for chk in self.res_checks.values():
            chk.set_active(state)
        self.updating_filters = False
        self.save_filter_state()
        self.apply_filters(reset_page=True)

    def on_reset_filters(self, btn):
        self.updating_filters = True
        self.chk_only_fav.set_active(False)
        self.chk_show_hidden.set_active(False)
        for chk in self.type_checks.values():
            chk.set_active(True)
        for chk in self.rating_checks.values():
            chk.set_active(True)
        for chk in self.tag_checks.values():
            chk.set_active(True)
        for chk in self.res_checks.values():
            chk.set_active(True)
        self.search_entry.set_text("")
        self.updating_filters = False
        self.save_filter_state()
        self.apply_filters(reset_page=True)

    def position_and_show_filters(self):
        mx, my = self.get_position()
        _, mh = self.get_size()
        fx = max(0, mx - 262)
        self.filter_win.resize(255, mh)
        self.filter_win.move(fx, my)
        self.filter_win.show_all()
        return False

    def on_filter_win_close(self, widget, event):
        self.btn_sidebar.set_active(False)
        return True

    def on_sidebar_toggled(self, btn):
        visible = btn.get_active()
        if visible:
            self.position_and_show_filters()
        else:
            self.filter_win.hide()
        self.app_settings["show_sidebar"] = visible
        save_settings(self.app_settings)

    def on_key_press_event(self, widget, event):
        if event.keyval == Gdk.KEY_F5:
            self.refresh_gallery()
            return True
        if event.keyval == Gdk.KEY_F9:
            self.btn_sidebar.set_active(not self.btn_sidebar.get_active())
            return True
        if event.keyval in (Gdk.KEY_f, Gdk.KEY_F, Gdk.KEY_Cyrillic_a, Gdk.KEY_Cyrillic_A) and not self.search_entry.has_focus():
            self.on_toggle_favorite_clicked(None)
            return True
        if event.keyval == Gdk.KEY_Delete and not self.search_entry.has_focus():
            self.on_toggle_hidden_clicked(None)
            return True
        return False

    def refresh_gallery(self):
        self.preload_data()
        self.apply_filters(reset_page=False)

    def item_matches_filters(self, wp_id, title):
        if wp_id in self.app_settings.get("hidden", []) and not self.chk_show_hidden.get_active():
            return False

        if self.chk_only_fav.get_active() and wp_id not in self.app_settings.get("favorites", []):
            return False

        if self.search_query and self.search_query not in title.lower():
            return False

        meta = self.meta_map.get(wp_id, {})

        w_type = meta.get("type", "scene")
        if w_type in self.type_checks and not self.type_checks[w_type].get_active():
            return False

        rating = meta.get("rating", "everyone")
        if rating in self.rating_checks and not self.rating_checks[rating].get_active():
            return False

        item_tags = meta.get("tags", ["unspecified"])
        if not any(t in self.tag_checks and self.tag_checks[t].get_active() for t in item_tags):
            return False

        res = meta.get("res", "standard")
        if self.all_custom_props.get(wp_id, {}).get("__scaling__") == "portrait":
            res = "portrait"
        if res in self.res_checks and not self.res_checks[res].get_active():
            return False

        return True

    def apply_filters(self, reset_page=True, render=True):
        self.filtered_items = [
            item for item in self.items_data
            if self.item_matches_filters(item[0], item[1])
        ]
        if reset_page:
            self.current_page = 0
        if render:
            self.render_cards()

    def change_page(self, delta):
        total_pages = max(1, (len(self.filtered_items) + self.page_size - 1) // self.page_size)
        new_page = max(0, min(total_pages - 1, self.current_page + delta))
        if new_page != self.current_page:
            self.current_page = new_page
            self.render_cards()
            adj = self.gallery_scroll.get_vadjustment()
            if adj:
                adj.set_value(0)

    def on_search_changed(self, entry):
        self.search_query = entry.get_text().strip().lower()
        self.apply_filters(reset_page=True)

    def detect_tags(self, pdata):
        raw_tags = pdata.get("tags", [])
        if not isinstance(raw_tags, list):
            raw_tags = []
        norm_tags = [str(t).strip().lower() for t in raw_tags]

        matched = set()
        for key, _, aliases in TAG_DEFINITIONS:
            if any(alias in norm_tags for alias in aliases):
                matched.add(key)

        if not matched:
            matched.add("unspecified")
        return list(matched)

    def detect_resolution(self, wp_id, title, pdata):
        if self.all_custom_props.get(wp_id, {}).get("__scaling__") == "portrait":
            return "portrait"

        tags = pdata.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        blob = f"{title} {pdata.get('description', '')} {' '.join(str(t) for t in tags)}".lower()

        if any(k in blob for k in ("3840", "2160", "4k", "uhd")):
            return "4k"
        if any(k in blob for k in ("2560", "1440", "2k", "qhd")):
            return "1440p"
        if any(k in blob for k in ("1920", "1080", "fhd", "full hd", "fullhd")):
            return "1080p"
        if any(k in blob for k in ("1366", "768")):
            return "768p"
        if any(k in blob for k in ("1280", "720", "720p")):
            return "720p"
        if any(k in blob for k in ("portrait", "9:16", "mobile", "vertical", "phone")):
            return "portrait"
        return "standard"

    def preload_data(self):
        if not os.path.exists(WORKSHOP_DIR):
            return

        self.raw_props_cache.clear()
        self.img_paths_map.clear()
        self.meta_map.clear()
        raw_list = []

        for item in os.listdir(WORKSHOP_DIR):
            path = os.path.join(WORKSHOP_DIR, item)
            if not os.path.isdir(path):
                continue

            title = f"Сцена {item}"
            pdata = {}
            pjson = os.path.join(path, "project.json")
            if os.path.exists(pjson):
                try:
                    with open(pjson, "r", encoding="utf-8", errors="ignore") as f:
                        pdata = json.load(f)
                        title = pdata.get("title", title)
                        props = pdata.get("general", {}).get("properties", {})
                        if props:
                            self.raw_props_cache[item] = props
                except Exception:
                    pass

            w_type = str(pdata.get("type", "scene")).strip().lower()
            if w_type not in ("scene", "video", "web", "application"):
                w_type = "scene"

            raw_rating = str(pdata.get("contentrating", "Everyone")).strip().lower()
            if "mature" in raw_rating:
                rating = "mature"
            elif "questionable" in raw_rating:
                rating = "questionable"
            else:
                rating = "everyone"

            res = self.detect_resolution(item, title, pdata)
            item_tags = self.detect_tags(pdata)

            self.meta_map[item] = {
                "type": w_type,
                "rating": rating,
                "res": res,
                "tags": item_tags
            }

            img_path = None
            if "preview" in pdata and pdata["preview"]:
                candidate = os.path.join(path, pdata["preview"])
                if os.path.exists(candidate):
                    img_path = candidate

            if not img_path:
                try:
                    for f in os.listdir(path):
                        if f.lower().endswith(('.gif', '.jpg', '.jpeg', '.png', '.webp')):
                            img_path = os.path.join(path, f)
                            break
                except Exception:
                    pass

            self.img_paths_map[item] = img_path
            mtime = os.path.getmtime(path)
            raw_list.append({
                "id": item,
                "title": title,
                "img_path": img_path,
                "mtime": mtime
            })

        sort_mode = self.app_settings.get("sort_by", "newest")
        if sort_mode == "newest":
            raw_list.sort(key=lambda x: x["mtime"], reverse=True)
        elif sort_mode == "name":
            raw_list.sort(key=lambda x: x["title"].lower())
        else:
            raw_list.sort(key=lambda x: x["id"])

        self.items_data = [(x["id"], x["title"], x["img_path"], x["mtime"]) for x in raw_list]

    def get_or_create_pixbuf(self, item, img_path, mtime, w, h):
        cache_file = os.path.join(THUMB_CACHE_DIR, f"{item}_{w}x{h}.png")

        if os.path.exists(cache_file) and os.path.getmtime(cache_file) >= mtime:
            try:
                return GdkPixbuf.Pixbuf.new_from_file(cache_file)
            except Exception:
                pass

        if img_path and os.path.exists(img_path):
            try:
                with Image.open(img_path) as im:
                    im.seek(0)
                    fitted = ImageOps.fit(im.convert("RGBA"), (w, h), Image.Resampling.BILINEAR)
                    fitted.save(cache_file, "PNG")
                return GdkPixbuf.Pixbuf.new_from_file(cache_file)
            except Exception:
                pass

        pixbuf = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, True, 8, w, h)
        pixbuf.fill(0x24272eff)
        return pixbuf

    def on_window_close(self, widget, event):
        w, h = self.get_size()
        self.app_settings["win_width"] = w
        self.app_settings["win_height"] = h
        save_settings(self.app_settings)
        return False

    def schedule_grid_layout(self):
        if self._layout_idle_id:
            return
        self._layout_idle_id = GLib.idle_add(self._apply_grid_layout)

    def _apply_grid_layout(self):
        self._layout_idle_id = 0
        alloc_w = self.gallery_scroll.get_allocated_width()
        if alloc_w <= 50:
            return False
        avail = alloc_w - 22
        w = SIZES[self.current_size_name][0]
        item_w = w + 8
        cols = max(1, (avail + 6) // (item_w + 6))
        sp = max(6, (avail - cols * item_w) // (cols - 1)) if cols > 1 else 6
        sig = (cols, sp, w)
        if sig != self._last_grid_sig:
            self._last_grid_sig = sig
            self.iconview.set_columns(1)
            self.iconview.set_item_width(w)
            self.iconview.set_columns(cols)
            self.iconview.set_column_spacing(sp)
            self.iconview.queue_resize()
            self.iconview.queue_draw()
        return False

    def on_gallery_size_allocate(self, widget, alloc):
        self.schedule_grid_layout()

    def render_cards(self):
        self.page_size = PAGE_SIZES.get(self.current_size_name, 24)
        self.model.clear()
        total = len(self.filtered_items)
        total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.current_page = max(0, min(self.current_page, total_pages - 1))

        start = self.current_page * self.page_size
        page_items = self.filtered_items[start:start + self.page_size]

        w, h = SIZES[self.current_size_name]
        self.iconview.set_columns(1)
        self.iconview.set_item_width(w)
        for item, title, img_path, mtime in page_items:
            pixbuf = self.get_or_create_pixbuf(item, img_path, mtime, w, h)
            self.model.append([item, title, pixbuf])

        self._last_grid_sig = None
        self.schedule_grid_layout()

        self.lbl_page_info.set_text(f"Страница {self.current_page + 1} из {total_pages}  ({total})")
        self.btn_prev_page.set_sensitive(self.current_page > 0)
        self.btn_next_page.set_sensitive(self.current_page < total_pages - 1)

    def on_size_toggled(self, size_name):
        if self.current_size_name != size_name:
            self.current_size_name = size_name
            self.app_settings["size"] = size_name
            save_settings(self.app_settings)
            self.page_size = PAGE_SIZES.get(size_name, 24)
            self.render_cards()

    def on_settings_clicked(self, btn):
        dialog = SettingsDialog(self, self.app_settings)
        if dialog.run() == Gtk.ResponseType.OK:
            self.app_settings.update(dialog.get_values())
            save_settings(self.app_settings)
            dialog.destroy()
            self.preload_data()
            self.render_cards()
        else:
            dialog.destroy()

    def get_selected_id_and_title(self):
        selected = self.iconview.get_selected_items()
        if selected:
            it = self.model.get_iter(selected[0])
            return self.model.get_value(it, 0), self.model.get_value(it, 1)
        return None, None

    def select_initial_active_wallpaper(self):
        active_id = None
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    active_id = f.read().strip()
            except Exception:
                pass
        if not active_id and self.items_data:
            active_id = self.items_data[0][0]
        if not active_id:
            return

        idx = next((i for i, x in enumerate(self.filtered_items) if x[0] == active_id), None)
        if idx is not None:
            self.current_page = idx // self.page_size
        self.render_cards()

        it = self.model.get_iter_first()
        found_in_grid = False
        while it:
            if self.model.get_value(it, 0) == active_id:
                path = self.model.get_path(it)
                self.iconview.select_path(path)
                self.iconview.scroll_to_path(path, False, 0.0, 0.0)
                found_in_grid = True
                break
            it = self.model.iter_next(it)

        if not found_in_grid:
            title = next((t for i, t, _, _ in self.items_data if i == active_id), f"Сцена {active_id}")
            self.load_inspector(active_id, title)

    def on_selection_changed(self, iconview):
        wp_id, wp_title = self.get_selected_id_and_title()
        if wp_id:
            self.load_inspector(wp_id, wp_title)

    def update_fav_button_label(self):
        favs = self.app_settings.get("favorites", [])
        if self.insp_wp_id in favs:
            self.btn_insp_fav.set_label("★ В избранном")
        else:
            self.btn_insp_fav.set_label("☆ В избранное")

    def on_toggle_favorite_clicked(self, btn):
        if not self.insp_wp_id:
            return
        favs = list(self.app_settings.get("favorites", []))
        if self.insp_wp_id in favs:
            favs.remove(self.insp_wp_id)
        else:
            favs.append(self.insp_wp_id)
        self.app_settings["favorites"] = favs
        save_settings(self.app_settings)
        self.update_fav_button_label()
        if self.chk_only_fav.get_active():
            self.apply_filters(reset_page=False)

    def update_hide_button_label(self):
        hidden = self.app_settings.get("hidden", [])
        if self.insp_wp_id in hidden:
            self.btn_insp_hide.set_label("👁 Вернуть")
        else:
            self.btn_insp_hide.set_label("🚫 Скрыть")

    def on_toggle_hidden_clicked(self, btn):
        if not self.insp_wp_id:
            return
        hidden = list(self.app_settings.get("hidden", []))
        if self.insp_wp_id in hidden:
            hidden.remove(self.insp_wp_id)
        else:
            hidden.append(self.insp_wp_id)
        self.app_settings["hidden"] = hidden
        save_settings(self.app_settings)
        self.update_hide_button_label()
        self.apply_filters(reset_page=False)
        it = self.model.get_iter_first()
        if it:
            self.iconview.select_path(self.model.get_path(it))

    def on_inspector_widget_scroll(self, widget, event):
        adj = self.right_scroll.get_vadjustment()
        if adj:
            step = adj.get_step_increment() or 40.0
            max_val = max(adj.get_lower(), adj.get_upper() - adj.get_page_size())
            if event.direction == Gdk.ScrollDirection.UP:
                adj.set_value(max(adj.get_lower(), adj.get_value() - step))
            elif event.direction == Gdk.ScrollDirection.DOWN:
                adj.set_value(min(max_val, adj.get_value() + step))
            elif event.direction == Gdk.ScrollDirection.SMOOTH:
                ok, _, dy = event.get_scroll_deltas()
                if ok:
                    adj.set_value(max(adj.get_lower(), min(max_val, adj.get_value() + dy * step)))
        return True

    def update_playlist_add_button(self):
        if not hasattr(self, "btn_pl_add"):
            return
        pl = self.app_settings.get("playlist", [])
        if self.insp_wp_id in pl:
            self.btn_pl_add.set_label("✓ В плейлисте")
        else:
            self.btn_pl_add.set_label("+ Добавить выбранную")

    def scroll_playlist_to_index(self, idx, total):
        def _do_scroll():
            hadj = self.pl_scroll.get_hadjustment()
            if hadj:
                max_val = max(hadj.get_lower(), hadj.get_upper() - hadj.get_page_size())
                if total <= 1 or idx >= total - 1:
                    hadj.set_value(max_val)
                else:
                    hadj.set_value(max_val * (idx / (total - 1)))
            return False
        GLib.timeout_add(35, _do_scroll)

    def load_inspector(self, wp_id, wp_title):
        self.insp_wp_id = wp_id
        self.update_fav_button_label()
        self.update_hide_button_label()
        self.update_playlist_add_button()
        self.insp_title.set_text(wp_title)

        img_path = self.img_paths_map.get(wp_id)
        pb = self.get_or_create_pixbuf(wp_id, img_path, 0, 285, 165)
        self.insp_image.set_from_pixbuf(pb)

        meta = self.meta_map.get(wp_id, {})
        type_names = {"scene": "Сцена", "video": "Видео", "web": "Веб", "application": "Приложение"}
        rating_names = {"everyone": "0+", "questionable": "12+", "mature": "18+"}
        tag_map = {k: lbl for k, lbl, _ in TAG_DEFINITIONS}
        tags_str = ", ".join(tag_map.get(t, t) for t in meta.get("tags", []))
        t_lbl = type_names.get(meta.get("type", "scene"), "Сцена")
        r_lbl = rating_names.get(meta.get("rating", "everyone"), "0+")
        self.insp_meta.set_text(f"{t_lbl} • {r_lbl} • ID: {wp_id}\n{tags_str}")

        for child in self.insp_props_box.get_children():
            self.insp_props_box.remove(child)
        self.insp_widget_map.clear()

        current_values = self.all_custom_props.get(wp_id, {})
        raw_props = self.raw_props_cache.get(wp_id, {})

        box_scale = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box_scale.pack_start(Gtk.Label(label="Выравнивание:", halign=Gtk.Align.START), False, False, 0)
        self.insp_combo_scale = Gtk.ComboBoxText()
        self.insp_combo_scale.append("fill", "Заполнить (Fill)")
        self.insp_combo_scale.append("portrait", "Портрет 9:16 (По центру)")
        self.insp_combo_scale.append("stretch", "Растянуть (Stretch)")
        self.insp_combo_scale.set_active_id(current_values.get("__scaling__", "fill"))
        self.insp_combo_scale.connect("scroll-event", self.on_inspector_widget_scroll)
        box_scale.pack_start(self.insp_combo_scale, False, False, 0)
        self.insp_props_box.pack_start(box_scale, False, False, 0)

        sorted_keys = sorted(
            raw_props.keys(),
            key=lambda k: raw_props[k].get("order", raw_props[k].get("index", 999))
        )

        for key in sorted_keys:
            prop = raw_props[key]
            p_type = prop.get("type")
            raw_title = str(prop.get("text", key))
            title = re.sub(r'<[^>]+>', '', raw_title).strip() or key
            if title == "ui_browse_properties_scheme_color" or key == "schemecolor":
                title = "Цветовая схема"
            val = current_values.get(key, prop.get("value"))

            if p_type == "bool":
                chk = Gtk.CheckButton(label=title)
                lbl_c = chk.get_child()
                if isinstance(lbl_c, Gtk.Label):
                    lbl_c.set_line_wrap(True)
                    lbl_c.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                    lbl_c.set_max_width_chars(30)
                    lbl_c.set_xalign(0.0)
                chk.set_active(bool(val))
                self.insp_props_box.pack_start(chk, False, False, 0)
                self.insp_widget_map[key] = ("bool", chk)

            elif p_type == "slider":
                p_min = float(prop.get("min", 0))
                p_max = float(prop.get("max", 100))
                is_fraction = prop.get("fraction", False)
                step = 0.1 if is_fraction else 1.0
                row_b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                lbl_s = Gtk.Label(label=f"{title}:", halign=Gtk.Align.START)
                lbl_s.set_line_wrap(True)
                lbl_s.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_s.set_max_width_chars(30)
                lbl_s.set_xalign(0.0)
                row_b.pack_start(lbl_s, False, False, 0)
                scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, p_min, p_max, step)
                scale.set_digits(1 if is_fraction else 0)
                try:
                    scale.set_value(float(val if val is not None else p_min))
                except Exception:
                    scale.set_value(p_min)
                scale.connect("scroll-event", self.on_inspector_widget_scroll)
                row_b.pack_start(scale, False, False, 0)
                self.insp_props_box.pack_start(row_b, False, False, 0)
                self.insp_widget_map[key] = ("slider", scale, is_fraction)

            elif p_type == "combo":
                row_b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                lbl_p = Gtk.Label(label=f"{title}:", halign=Gtk.Align.START)
                lbl_p.set_line_wrap(True)
                lbl_p.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_p.set_max_width_chars(28)
                lbl_p.set_xalign(0.0)
                row_b.pack_start(lbl_p, False, False, 0)
                combo = Gtk.ComboBoxText()
                for opt in prop.get("options", []):
                    o_val = str(opt.get("value", ""))
                    combo.append(o_val, opt.get("label", o_val))
                combo.set_active_id(str(val))
                combo.connect("scroll-event", self.on_inspector_widget_scroll)
                row_b.pack_start(combo, False, False, 0)
                self.insp_props_box.pack_start(row_b, False, False, 0)
                self.insp_widget_map[key] = ("combo", combo)

            elif p_type == "color":
                row_b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                lbl_p = Gtk.Label(label=f"{title}:", halign=Gtk.Align.START)
                lbl_p.set_line_wrap(True)
                lbl_p.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_p.set_max_width_chars(28)
                lbl_p.set_xalign(0.0)
                row_b.pack_start(lbl_p, True, True, 0)
                btn_color = Gtk.ColorButton()
                try:
                    parts = [float(x) for x in str(val).split()]
                    btn_color.set_rgba(Gdk.RGBA(parts[0], parts[1], parts[2], 1.0))
                except Exception:
                    pass
                row_b.pack_start(btn_color, False, False, 0)
                self.insp_props_box.pack_start(row_b, False, False, 0)
                self.insp_widget_map[key] = ("color", btn_color)

            elif p_type == "textinput":
                row_b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
                lbl_p = Gtk.Label(label=f"{title}:", halign=Gtk.Align.START)
                lbl_p.set_line_wrap(True)
                lbl_p.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                lbl_p.set_max_width_chars(28)
                lbl_p.set_xalign(0.0)
                row_b.pack_start(lbl_p, False, False, 0)
                entry = Gtk.Entry()
                entry.set_text(str(val if val is not None else ""))
                row_b.pack_start(entry, False, False, 0)
                self.insp_props_box.pack_start(row_b, False, False, 0)
                self.insp_widget_map[key] = ("textinput", entry)

        self.insp_props_box.show_all()

    def extract_inspector_values(self):
        result = {"__scaling__": self.insp_combo_scale.get_active_id() or "fill"}
        for key, entry in self.insp_widget_map.items():
            w_type = entry[0]
            if w_type == "bool":
                result[key] = entry[1].get_active()
            elif w_type == "slider":
                val = entry[1].get_value()
                result[key] = float(val) if entry[2] else int(val)
            elif w_type == "combo":
                result[key] = entry[1].get_active_id()
            elif w_type == "color":
                rgba = entry[1].get_rgba()
                result[key] = f"{rgba.red:.3f} {rgba.green:.3f} {rgba.blue:.3f}"
            elif w_type == "textinput":
                result[key] = entry[1].get_text()
        return result

    def on_insp_apply_clicked(self, btn):
        if not self.insp_wp_id:
            return
        self.all_custom_props[self.insp_wp_id] = self.extract_inspector_values()
        save_all_custom_properties(self.all_custom_props)
        self.apply_wallpaper(self.insp_wp_id)
        self.apply_filters(reset_page=True)

    def on_insp_reset_clicked(self, btn):
        if not self.insp_wp_id:
            return
        if self.insp_wp_id in self.all_custom_props:
            del self.all_custom_props[self.insp_wp_id]
            save_all_custom_properties(self.all_custom_props)
        self.load_inspector(self.insp_wp_id, self.insp_title.get_text())
        self.apply_wallpaper(self.insp_wp_id)
        self.apply_filters(reset_page=True)

    def sync_playlist_daemon(self):
        subprocess.run(["pkill", "-f", "wallpaper-playlist.sh"], check=False)
        pl = self.app_settings.get("playlist", [])
        enabled = self.app_settings.get("playlist_enabled", False)
        if enabled and len(pl) >= 2 and os.path.exists(PLAYLIST_SCRIPT):
            subprocess.Popen(
                ["nohup", PLAYLIST_SCRIPT],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )

    def render_playlist_strip(self):
        for child in self.pl_strip_box.get_children():
            self.pl_strip_box.remove(child)

        pl = self.app_settings.get("playlist", [])
        interval = self.app_settings.get("playlist_interval", 15)
        order_lbl = "случайно" if self.app_settings.get("playlist_order") == "random" else "по порядку"
        self.lbl_pl_title.set_text(f"Плейлист ({len(pl)}) • каждые {interval} мин, {order_lbl}")

        if self.btn_pl_toggle.get_active():
            self.btn_pl_toggle.set_label("⏹ Остановить плейлист")
        else:
            self.btn_pl_toggle.set_label("▶ Запустить плейлист")

        if not pl:
            hint = Gtk.Label(label="Добавьте минимум 2 сцены, чтобы запустить автоматическую смену обоев")
            hint.get_style_context().add_class("inspector-meta")
            self.pl_strip_box.pack_start(hint, False, False, 6)
        else:
            title_map = {i: t for i, t, _, _ in self.items_data}
            for idx, wp_id in enumerate(pl):
                card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                img_path = self.img_paths_map.get(wp_id)
                pb = self.get_or_create_pixbuf(wp_id, img_path, 0, 96, 54)
                btn_item = Gtk.Button()
                btn_item.set_image(Gtk.Image.new_from_pixbuf(pb))
                btn_item.set_tooltip_text(f"{idx + 1}. {title_map.get(wp_id, wp_id)}")
                btn_item.connect("clicked", lambda b, wid=wp_id: self.apply_wallpaper(wid))

                btn_del = Gtk.Button(label="×")
                btn_del.get_style_context().add_class("playlist-del-btn")
                btn_del.set_tooltip_text("Убрать из плейлиста")
                btn_del.connect("clicked", lambda b, wid=wp_id: self.on_playlist_remove(wid))

                card.pack_start(btn_item, False, False, 0)
                card.pack_start(btn_del, False, False, 0)
                self.pl_strip_box.pack_start(card, False, False, 0)

        self.pl_strip_box.show_all()

    def on_playlist_add_clicked(self, btn):
        if not self.insp_wp_id:
            return
        pl = list(self.app_settings.get("playlist", []))
        if self.insp_wp_id not in pl:
            pl.append(self.insp_wp_id)
            self.app_settings["playlist"] = pl
            save_settings(self.app_settings)
            self.render_playlist_strip()
            self.sync_playlist_daemon()
            self.update_playlist_add_button()
            self.scroll_playlist_to_index(len(pl) - 1, len(pl))
        else:
            self.scroll_playlist_to_index(pl.index(self.insp_wp_id), len(pl))

    def on_playlist_remove(self, wp_id):
        pl = [x for x in self.app_settings.get("playlist", []) if x != wp_id]
        self.app_settings["playlist"] = pl
        if len(pl) < 2 and self.app_settings.get("playlist_enabled"):
            self.app_settings["playlist_enabled"] = False
            self.btn_pl_toggle.set_active(False)
        save_settings(self.app_settings)
        self.render_playlist_strip()
        self.sync_playlist_daemon()
        self.update_playlist_add_button()

    def on_playlist_clear_clicked(self, btn):
        self.app_settings["playlist"] = []
        self.app_settings["playlist_enabled"] = False
        save_settings(self.app_settings)
        self.btn_pl_toggle.set_active(False)
        self.render_playlist_strip()
        self.sync_playlist_daemon()
        self.update_playlist_add_button()

    def on_playlist_settings_clicked(self, btn):
        dlg = PlaylistSettingsDialog(self, self.app_settings)
        if dlg.run() == Gtk.ResponseType.OK:
            self.app_settings.update(dlg.get_values())
            save_settings(self.app_settings)
            self.render_playlist_strip()
            self.sync_playlist_daemon()
        dlg.destroy()

    def on_playlist_toggled(self, btn):
        active = btn.get_active()
        pl = self.app_settings.get("playlist", [])
        if active and len(pl) < 2:
            btn.set_active(False)
            return
        self.app_settings["playlist_enabled"] = active
        save_settings(self.app_settings)
        self.render_playlist_strip()
        self.sync_playlist_daemon()
        self.update_playlist_add_button()
        if active and pl:
            self.apply_wallpaper(pl[0])

    def apply_wallpaper(self, wp_id):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(wp_id)
        active_props = self.all_custom_props.get(wp_id, {})
        scaling = active_props.get("__scaling__", "fill")

        if scaling == "portrait":
            img_path = self.img_paths_map.get(wp_id)
            generate_blurred_backdrop(img_path)

        export_env(self.app_settings, active_props)
        subprocess.Popen([RUN_SCRIPT])

    def on_item_activated(self, iconview, path):
        it = self.model.get_iter(path)
        self.apply_wallpaper(self.model.get_value(it, 0))

    def on_apply_clicked(self, btn):
        wp_id, _ = self.get_selected_id_and_title()
        if wp_id:
            self.apply_wallpaper(wp_id)

if __name__ == "__main__":
    win = WallpaperGallery()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
