"""Keyboard shortcut editor dialog."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk
from .config import SHORTCUT_NAMES

class ShortcutEditorDialog(Adw.Window):
    def __init__(self, parent, config, callback):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("Edit Keyboard Shortcuts")
        self.set_default_size(400, 300)
        
        self.config = config
        self.callback = callback
        self.waiting_for_key_action = None

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content)

        header = Adw.HeaderBar()
        content.append(header)
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        list_box.set_margin_start(12)
        list_box.set_margin_end(12)
        list_box.set_margin_top(12)
        list_box.set_margin_bottom(12)
        content.append(list_box)

        self.rows = {}
        for action, name in SHORTCUT_NAMES.items():
            row = Adw.ActionRow(title=name)
            
            shortcut_label = Gtk.Label(label=config.get_shortcut_label(action))
            shortcut_label.add_css_class("keycap")
            row.add_suffix(shortcut_label)
            
            row.set_activatable(True)
            row.connect("activated", self._on_row_activated, action)
            
            list_box.append(row)
            self.rows[action] = shortcut_label

        # Key listener
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    def _on_row_activated(self, row, action):
        self.waiting_for_key_action = action
        self.rows[action].set_label("?")
        self.rows[action].add_css_class("waiting")

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if self.waiting_for_key_action:
            action = self.waiting_for_key_action
            self.config.shortcuts[action] = keyval
            self.rows[action].set_label(self.config.get_shortcut_label(action))
            self.rows[action].remove_css_class("waiting")
            self.waiting_for_key_action = None
            self.callback()
            return True
        return False
