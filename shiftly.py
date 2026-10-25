#!/usr/bin/env python3
"""Shiftly - cycles through named sit/stand phases and reminds you to switch."""
import json
import os
import subprocess
import sys
import time

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Notify", "0.7")
from gi.repository import Gio, GLib, Gtk, Notify

try:
    gi.require_version("XApp", "1.0")
    from gi.repository import XApp
except (ValueError, ImportError):
    XApp = None

APP_ID = "net.jacek_k.Shiftly"
CONFIG_PATH = os.path.join(
    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
    "shiftly",
    "config.json",
)
SOUND_FILE = "/usr/share/sounds/freedesktop/stereo/complete.oga"
DEFAULT_CONFIG = {
    "phases": [
        {"name": "Sitting", "minutes": 40},
        {"name": "Standing", "minutes": 20},
    ],
    "sound": True,
}


def load_config():
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        phases = [
            {"name": str(p["name"]), "minutes": float(p["minutes"])}
            for p in cfg["phases"]
            if float(p["minutes"]) > 0
        ]
        if phases:
            return {"phases": phases, "sound": bool(cfg.get("sound", True))}
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(cfg):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(cfg, f, indent=2)
    os.replace(tmp, CONFIG_PATH)


def fmt_minutes(m):
    return str(int(m)) if float(m).is_integer() else str(m)


def fmt_clock(seconds):
    seconds = max(0, int(seconds + 0.999))
    return f"{seconds // 60}:{seconds % 60:02d}"


class Cycle:
    """Timer state: which phase is active and how long is left in it."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.paused = False
        self.index = 0
        self.remaining = 0
        self.start_phase(0)

    @property
    def phase(self):
        return self.cfg["phases"][self.index]

    def start_phase(self, index):
        self.index = index % len(self.cfg["phases"])
        self.remaining = self.phase["minutes"] * 60

    def tick(self, elapsed):
        """Advance the clock; returns True when a phase just ended."""
        if self.paused:
            return False
        self.remaining -= elapsed
        if self.remaining <= 0:
            self.start_phase(self.index + 1)
            return True
        return False

    def apply_config(self, cfg):
        names = [p["name"] for p in cfg["phases"]]
        current = self.phase["name"]
        self.cfg = cfg
        if current in names:
            # keep the running phase and its remaining time if it still exists
            self.index = names.index(current)
        else:
            self.start_phase(0)


class Shiftly(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.cycle = None
        self.icon = None
        self.indicator = None
        self.last_tick = time.monotonic()
        self.settings_win = None

    # -- lifecycle ---------------------------------------------------------

    def do_startup(self):
        Gtk.Application.do_startup(self)
        Notify.init("Shiftly")
        self.cycle = Cycle(load_config())
        self.build_tray()
        self.refresh()
        GLib.timeout_add_seconds(1, self.on_tick)
        self.hold()

    def do_activate(self):
        # launching a second copy opens the settings of the running one
        self.show_settings()

    # -- tray --------------------------------------------------------------

    def build_tray(self):
        self.status_item = Gtk.MenuItem(sensitive=False)
        self.pause_item = Gtk.MenuItem()
        self.pause_item.connect("activate", lambda *_: self.toggle_pause())
        skip_item = Gtk.MenuItem(label="Skip to next phase")
        skip_item.connect("activate", lambda *_: self.start_phase(self.cycle.index + 1))
        self.start_item = Gtk.MenuItem(label="Start phase")
        settings_item = Gtk.MenuItem(label="Settings…")
        settings_item.connect("activate", lambda *_: self.show_settings())
        quit_item = Gtk.MenuItem(label="Quit")
        quit_item.connect("activate", lambda *_: self.quit())

        self.menu = Gtk.Menu()
        for item in (
            self.status_item,
            Gtk.SeparatorMenuItem(),
            self.pause_item,
            skip_item,
            self.start_item,
            Gtk.SeparatorMenuItem(),
            settings_item,
            quit_item,
        ):
            self.menu.append(item)
        self.menu.show_all()

        if XApp is not None:
            self.icon = XApp.StatusIcon()
            self.icon.set_primary_menu(self.menu)
            self.icon.set_secondary_menu(self.menu)
        else:
            self.icon = Gtk.StatusIcon()
            self.icon.connect("popup-menu", self.on_legacy_popup)
            self.icon.connect("activate", self.on_legacy_popup, 0, 0)

    def on_legacy_popup(self, icon, button, time_):
        self.menu.popup(None, None, Gtk.StatusIcon.position_menu, icon, button, time_)

    def rebuild_start_submenu(self):
        sub = Gtk.Menu()
        for i, p in enumerate(self.cycle.cfg["phases"]):
            item = Gtk.MenuItem(label=f"{p['name']} ({fmt_minutes(p['minutes'])} min)")
            item.connect("activate", lambda _w, idx=i: self.start_phase(idx))
            sub.append(item)
        sub.show_all()
        self.start_item.set_submenu(sub)

    # -- actions -----------------------------------------------------------

    def toggle_pause(self):
        self.cycle.paused = not self.cycle.paused
        self.refresh()

    def start_phase(self, index):
        self.cycle.start_phase(index)
        self.cycle.paused = False
        self.refresh()

    def on_tick(self):
        now = time.monotonic()
        elapsed = min(now - self.last_tick, 5)  # don't jump after a long stall
        self.last_tick = now
        if self.cycle.tick(elapsed):
            self.announce()
        self.refresh()
        return True

    def announce(self):
        p = self.cycle.phase
        body = f"{p['name']} for {fmt_minutes(p['minutes'])} min"
        n = Notify.Notification.new("Time to change position", body, "dialog-information")
        n.set_urgency(Notify.Urgency.CRITICAL)
        try:
            n.show()
        except GLib.Error:
            pass
        if self.cycle.cfg["sound"] and os.path.exists(SOUND_FILE):
            subprocess.Popen(
                ["paplay", SOUND_FILE],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    def refresh(self):
        c = self.cycle
        state = " (paused)" if c.paused else ""
        text = f"{c.phase['name']} {fmt_clock(c.remaining)}{state}"
        self.status_item.set_label(text)
        self.pause_item.set_label("Resume" if c.paused else "Pause")
        icon_name = (
            "media-playback-pause-symbolic"
            if c.paused
            else "preferences-system-time-symbolic"
        )
        if XApp is not None:
            self.icon.set_icon_name(icon_name)
            self.icon.set_label(text)
            self.icon.set_tooltip_text(text)
        else:
            self.icon.set_from_icon_name(icon_name)
            self.icon.set_tooltip_text(text)
        names = tuple((p["name"], p["minutes"]) for p in c.cfg["phases"])
        if names != getattr(self, "_menu_phases", None):
            self._menu_phases = names
            self.rebuild_start_submenu()

    # -- settings ----------------------------------------------------------

    def show_settings(self):
        if self.settings_win is None:
            self.settings_win = SettingsWindow(self)
            self.settings_win.connect("destroy", self.on_settings_closed)
        self.settings_win.present()

    def on_settings_closed(self, *_):
        self.settings_win = None

    def apply_settings(self, cfg):
        save_config(cfg)
        self.cycle.apply_config(cfg)
        self.refresh()


class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="Shiftly settings", default_width=420, default_height=360)
        self.app = app
        self.set_icon_name("preferences-system-time")

        self.store = Gtk.ListStore(str, str)  # name, minutes (as text)
        for p in app.cycle.cfg["phases"]:
            self.store.append([p["name"], fmt_minutes(p["minutes"])])

        self.view = Gtk.TreeView(model=self.store)
        for col, title in ((0, "Phase name"), (1, "Minutes")):
            r = Gtk.CellRendererText(editable=True)
            r.connect("edited", self.on_edited, col)
            c = Gtk.TreeViewColumn(title, r, text=col)
            c.set_expand(col == 0)
            self.view.append_column(c)

        scroll = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN, vexpand=True)
        scroll.add(self.view)

        buttons = Gtk.Box(spacing=6)
        for label, handler in (
            ("Add", self.on_add),
            ("Remove", self.on_remove),
            ("Up", lambda *_: self.move(-1)),
            ("Down", lambda *_: self.move(1)),
        ):
            b = Gtk.Button(label=label)
            b.connect("clicked", handler)
            buttons.pack_start(b, False, False, 0)

        self.sound = Gtk.CheckButton(label="Play a sound on phase change")
        self.sound.set_active(app.cycle.cfg["sound"])

        save = Gtk.Button(label="Save")
        save.get_style_context().add_class("suggested-action")
        save.connect("clicked", self.on_save)
        close = Gtk.Button(label="Close")
        close.connect("clicked", lambda *_: self.destroy())
        bottom = Gtk.Box(spacing=6)
        bottom.pack_end(save, False, False, 0)
        bottom.pack_end(close, False, False, 0)

        self.hint = Gtk.Label(
            label="Phases run top to bottom, then repeat.", xalign=0
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin=12)
        for w in (self.hint, scroll, buttons, self.sound, bottom):
            box.pack_start(w, w is scroll, True, 0)
        self.add(box)
        self.show_all()

    def on_edited(self, _renderer, path, text, col):
        text = text.strip()
        if col == 1:
            try:
                if float(text) <= 0:
                    raise ValueError
            except ValueError:
                return
        elif not text:
            return
        self.store[path][col] = text

    def on_add(self, *_):
        it = self.store.append(["New phase", "30"])
        path = self.store.get_path(it)
        self.view.set_cursor(path, self.view.get_column(0), True)

    def on_remove(self, *_):
        model, it = self.view.get_selection().get_selected()
        if it is not None and len(model) > 1:
            model.remove(it)

    def move(self, direction):
        model, it = self.view.get_selection().get_selected()
        if it is None:
            return
        other = model.iter_next(it) if direction > 0 else None
        if direction < 0:
            path = model.get_path(it)
            if path.prev():
                other = model.get_iter(path)
        if other is not None:
            model.swap(it, other)

    def on_save(self, *_):
        phases = [
            {"name": row[0], "minutes": float(row[1])} for row in self.store
        ]
        self.app.apply_settings({"phases": phases, "sound": self.sound.get_active()})
        self.hint.set_text("Saved.")


if __name__ == "__main__":
    sys.exit(Shiftly().run(sys.argv))
