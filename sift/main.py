#!/usr/bin/env python3
"""Sift – GNOME file triage app."""

import sys
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, Gio, GLib
from pathlib import Path

# Resolve package path so we can run directly
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

from sift.window import SiftWindow

APP_ID = "io.github.frephs.Sift"


class SiftApp(Adw.Application):
    """Top-level Adw.Application."""

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )

    def do_startup(self):
        Adw.Application.do_startup(self)
        self._load_css()
        GLib.set_application_name("Sift")
        GLib.set_prgname(APP_ID)
        
        # Add local icon to theme EARLY
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_dir = _HERE / "resources"
        if str(icon_dir) not in icon_theme.get_search_path():
            icon_theme.add_search_path(str(icon_dir))
        
        # Force default icon for all windows
        Gtk.Window.set_default_icon_name(APP_ID)

    def do_activate(self):
        win = self.get_active_window()
        if win is None:
            win = SiftWindow(app=self)
        win.present()

    def _load_css(self):
        css_path = _HERE / "style.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )


def main():
    app = SiftApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
