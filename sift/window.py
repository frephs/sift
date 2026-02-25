"""Main application window — layout, header bar, card stack, recent folders."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, Gio, GLib
from pathlib import Path

from .file_card import FileCard
from .file_manager import FileManager
from .config import Config, SHORTCUT_NAMES, RecentFolders
from .shortcuts import ShortcutEditorDialog


class SiftWindow(Adw.ApplicationWindow):
    """Primary application window."""

    def __init__(self, app: Adw.Application, **kwargs):
        super().__init__(application=app, **kwargs)
        self.set_default_size(480, 780)
        self.set_title("Sift")
        self.set_icon_name("com.github.frephs.Sift")

        self._files: list[Gio.File] = []
        self._current_index = 0
        self._source_dir: str | None = None
        self._directory: str | None = None
        self._recent = RecentFolders()  # destination folders
        self._recent_sources = RecentFolders("recent_sources.json")
        self._pending_file: Gio.File | None = None
        self._pending_trash: Gio.File | None = None
        self._trash_toast: Adw.Toast | None = None
        self._config = Config()

        # ── Root layout ──────────────────────────────────────────────
        self._toast_overlay = Adw.ToastOverlay()
        self.set_content(self._toast_overlay)

        self._root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay.set_child(self._root_box)

        # ── Header bar ───────────────────────────────────────────────
        self._header = Adw.HeaderBar()

        # Folder button (left)
        self._folder_btn = Gtk.Button(icon_name="folder-open-symbolic")
        self._folder_btn.set_tooltip_text("Open Folder")
        self._folder_btn.add_css_class("flat")
        self._folder_btn.connect("clicked", self._on_open_folder)
        self._header.pack_start(self._folder_btn)

        # Title container
        self._title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._title_box.set_valign(Gtk.Align.CENTER)
        
        # App icon (branded)
        self._app_icon_img = Gtk.Image.new_from_icon_name("com.github.frephs.Sift")
        self._app_icon_img.set_pixel_size(24)
        self._app_icon_img.update_property([Gtk.AccessibleProperty.LABEL], ["Application Icon"])
        self._title_box.append(self._app_icon_img)
        
        # App name label
        self._app_name_label = Gtk.Label(label="Sift")
        self._app_name_label.add_css_class("title")
        self._title_box.append(self._app_name_label)
        
        # Counter badge
        self._counter_label = Gtk.Label(label="")
        self._counter_label.add_css_class("counter-badge")
        self._counter_label.set_visible(False)
        self._title_box.append(self._counter_label)
        
        self._header.set_title_widget(self._title_box)

        # Refresh button (right)
        self._refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        self._refresh_btn.add_css_class("flat")
        self._refresh_btn.set_tooltip_text("Refresh File List")
        self._refresh_btn.connect("clicked", self._on_refresh_clicked)
        self._header.pack_end(self._refresh_btn)

        # Primary Menu
        self._menu_btn = Gtk.MenuButton()
        self._menu_btn.set_icon_name("open-menu-symbolic")
        self._menu_btn.add_css_class("flat")
        
        menu = Gio.Menu()
        menu.append("Key Shortcuts...", "win.shortcuts")
        self._menu_btn.set_menu_model(menu)
        self._header.pack_end(self._menu_btn)

        # Actions
        shortcuts_action = Gio.SimpleAction.new("shortcuts", None)
        shortcuts_action.connect("activate", self._on_shortcuts_clicked)
        self.add_action(shortcuts_action)

        self._root_box.append(self._header)

        # Global progress bar (below navbar)
        self._progress_container = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_visible(False)
        self._progress_bar.add_css_class("main-progress-bar")
        self._progress_container.append(self._progress_bar)
        self._root_box.append(self._progress_container)

        # ── Content area (stack for empty state / card view) ─────────
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(250)
        self._stack.set_vexpand(True)
        self._root_box.append(self._stack)

        # Empty state: custom clickable layout
        self._empty_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._empty_page.set_vexpand(True)
        self._empty_page.set_valign(Gtk.Align.CENTER)
        self._empty_page.set_margin_top(48)
        self._empty_page.set_margin_bottom(48)

        self._empty_icon_btn = Gtk.Button()
        self._empty_icon_btn.set_halign(Gtk.Align.CENTER)
        self._empty_icon_btn.add_css_class("flat")
        self._empty_icon_btn.add_css_class("splash-button")
        
        empty_image = Gtk.Image.new_from_icon_name("folder-symbolic")
        empty_image.set_pixel_size(128)
        self._empty_icon_btn.set_child(empty_image)
        self._empty_icon_btn.set_tooltip_text("Click to select a folder")
        self._empty_icon_btn.update_property([Gtk.AccessibleProperty.LABEL], ["Select Folder"])
        self._empty_icon_btn.connect("clicked", self._on_open_folder)
        self._empty_page.append(self._empty_icon_btn)

        empty_title = Gtk.Label(label="Select a Folder")
        empty_title.add_css_class("title-1")
        self._empty_page.append(empty_title)

        empty_desc = Gtk.Label(label="Choose a folder to start organizing your files.")
        empty_desc.add_css_class("dim-label")
        self._empty_page.append(empty_desc)
        
        self._stack.add_named(self._empty_page, "empty")
        
        # Done state: custom clickable layout
        self._done_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self._done_page.set_vexpand(True)
        self._done_page.set_valign(Gtk.Align.CENTER)
        self._done_page.set_margin_top(48)
        self._done_page.set_margin_bottom(48)

        self._done_icon_btn = Gtk.Button()
        self._done_icon_btn.set_halign(Gtk.Align.CENTER)
        self._done_icon_btn.add_css_class("flat")
        self._done_icon_btn.add_css_class("splash-button")
        
        done_image = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        done_image.set_pixel_size(128)
        self._done_icon_btn.set_child(done_image)
        self._done_icon_btn.set_tooltip_text("All files sorted. Click to select another folder.")
        self._done_icon_btn.update_property([Gtk.AccessibleProperty.LABEL], ["All Done. Select another folder."])
        self._done_icon_btn.connect("clicked", self._on_open_folder)
        self._done_page.append(self._done_icon_btn)

        done_title = Gtk.Label(label="All Done!")
        done_title.add_css_class("title-1")
        self._done_page.append(done_title)

        done_desc = Gtk.Label(label="Every file in this folder has been sorted.")
        done_desc.add_css_class("dim-label")
        self._done_page.append(done_desc)
        
        self._stack.add_named(self._done_page, "done")

        self._build_start_recent_list()

        # Card view
        self._card_page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._card_page.set_vexpand(True)
        self._card_page.set_overflow(Gtk.Overflow.HIDDEN)

        # Card container (centered)
        self._card_container = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            margin_top=20,
            margin_bottom=10,
        )
        self._card_page.append(self._card_container)

        # Action buttons
        btn_box = Gtk.FlowBox(
            column_spacing=8,
            row_spacing=8,
            halign=Gtk.Align.CENTER,
            selection_mode=Gtk.SelectionMode.NONE,
        )
        btn_box.add_css_class("action-buttons")

        # Custom combined Trash button
        self._trash_combined = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self._trash_combined.add_css_class("action-btn-combined")
        self._trash_combined.add_css_class("trash-combined")
        
        self._trash_visit_btn = Gtk.Button(icon_name="user-trash-symbolic")
        self._trash_visit_btn.add_css_class("flat")
        self._trash_visit_btn.add_css_class("combined-left")
        self._trash_visit_btn.set_tooltip_text("Open Wastebasket")
        self._trash_visit_btn.connect("clicked", self._on_see_wastebasket)
        self._trash_combined.append(self._trash_visit_btn)

        self._trash_action_btn = Gtk.Button(label="Trash")
        self._trash_action_btn.add_css_class("flat")
        self._trash_action_btn.add_css_class("combined-right")
        self._trash_action_btn.add_css_class("destructive-action")
        self._trash_action_btn.connect("clicked", self._on_trash_clicked)
        self._trash_combined.append(self._trash_action_btn)
        
        btn_box.append(self._trash_combined)

        self._skip_btn = Gtk.Button()
        skip_content = Adw.ButtonContent(
            icon_name="go-next-symbolic",
            label="Skip",
        )
        self._skip_btn.set_child(skip_content)
        self._skip_btn.add_css_class("pill")
        self._skip_btn.add_css_class("action-btn-skip")
        self._skip_btn.connect("clicked", self._on_skip_clicked)
        btn_box.append(self._skip_btn)

        self._later_btn = Gtk.Button()
        later_content = Adw.ButtonContent(
            icon_name="alarm-symbolic",
            label="Later",
        )
        self._later_btn.set_child(later_content)
        self._later_btn.add_css_class("pill")
        self._later_btn.add_css_class("action-btn-later")
        self._later_btn.connect("clicked", self._on_later_clicked)
        btn_box.append(self._later_btn)

        self._organize_btn = Gtk.Button()
        organize_content = Adw.ButtonContent(
            icon_name="folder-symbolic",
            label="Organize",
        )
        self._organize_btn.set_child(organize_content)
        self._organize_btn.add_css_class("pill")
        self._organize_btn.add_css_class("action-btn-organize")
        self._organize_btn.connect("clicked", self._on_organize_clicked)
        btn_box.append(self._organize_btn)

        self._card_page.append(btn_box)
        
        self._update_button_tooltips()

        # Recent folders panel (scrollable)
        self._build_recent_panel()
        self._recent_scroller = Gtk.ScrolledWindow()
        self._recent_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._recent_scroller.set_propagate_natural_height(True)
        self._recent_scroller.set_child(self._recent_frame)
        self._recent_scroller.set_vexpand(True)
        self._recent_scroller.set_valign(Gtk.Align.END)
        
        self._card_page.append(self._recent_scroller)

        self._stack.add_named(self._card_page, "card")

        # Start with empty state
        self._stack.set_visible_child_name("empty")

        # ── Keyboard shortcuts ──────────────────────────────────────
        key_ctrl = Gtk.EventControllerKey.new()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_ctrl)

    # ── Keyboard shortcuts ──────────────────────────────────────────

    def _on_key_pressed(self, controller, keyval, keycode, state):
        if self._current_index >= len(self._files):
            return False
            
        # Match current config shortcuts (case-insensitive for letter keys)
        keyval_lower = Gdk.keyval_to_lower(keyval)
        
        if keyval_lower == self._config.shortcuts["trash"] or keyval == Gdk.KEY_Delete:
            self._do_trash(self._files[self._current_index])
            return True
        if keyval_lower == self._config.shortcuts["organize"]:
            self._do_organize_prompt(self._files[self._current_index])
            return True
        if keyval_lower == self._config.shortcuts["skip"]:
            self._do_skip()
            return True
        if keyval_lower == self._config.shortcuts["later"]:
            self._do_later()
            return True
        return False

    def _update_button_tooltips(self):
        """Update action button tooltips with current shortcuts."""
        self._trash_action_btn.set_tooltip_text(f"Move to Trash ({self._config.get_shortcut_label('trash')})")
        self._skip_btn.set_tooltip_text(f"Skip ({self._config.get_shortcut_label('skip')})")
        self._later_btn.set_tooltip_text(f"Later ({self._config.get_shortcut_label('later')})")
        self._organize_btn.set_tooltip_text(f"Organize ({self._config.get_shortcut_label('organize')})")

    def _update_progress(self, action: str, progress: float):
        """Update the global progress bar based on scroll/drag progress."""
        if progress <= 0:
            self._progress_bar.set_visible(False)
            return

        self._progress_bar.set_visible(True)
        self._progress_bar.set_fraction(progress)

        # Update color based on action
        for cls in ["progress-trash", "progress-organize", "progress-skip", "progress-later"]:
            self._progress_bar.remove_css_class(cls)
        
        # Progress bar colors
        if action:
            self._progress_bar.add_css_class(f"progress-{action}")
        
        # Panel is now visible at all times, no need for dynamic hiders here.

    # ── Header bar actions ──────────────────────────────────────────

    def _on_open_folder(self, _btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Folder to Organize")
        dialog.select_folder(self, None, self._on_folder_selected)

    def _on_see_wastebasket(self, _btn):
        Gtk.show_uri(self, "trash:///", Gdk.CURRENT_TIME)

    def _on_open_folder_clicked(self, _btn, folder_path):
        """Open a folder in the default file manager."""
        gio_file = Gio.File.new_for_path(folder_path)
        Gtk.show_uri(self, gio_file.get_uri(), Gdk.CURRENT_TIME)

    def _on_refresh_clicked(self, _btn):
        # Finalize any pending trash before reloading
        self._confirm_trash()
        if self._directory:
            self._load_files(self._directory)

    def _on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        if folder is None:
            return

        path = folder.get_path()
        self._source_dir = path
        self._load_files(path)

    # ── File loading ────────────────────────────────────────────────

    def _load_files(self, directory: str):
        self._directory = directory
        self._recent_sources.add(directory)
        self._files = FileManager.list_files(directory)
        self._current_index = 0

        # Update folder button label
        folder_name = Path(directory).name
        content = Adw.ButtonContent(
            icon_name="folder-open-symbolic",
            label=folder_name,
        )
        self._folder_btn.set_child(content)

        if not self._files:
            self._stack.set_visible_child_name("done")
            self._counter_label.set_visible(False)
            return

        self._update_counter()
        self._show_current_card()

    def _show_current_card(self):
        if self._current_index >= len(self._files):
            self._refresh_start_recent_list()
            self._stack.set_visible_child_name("done")
            self._counter_label.set_visible(False)
            return

        self._stack.set_visible_child_name("card")

        # Remove previous card
        child = self._card_container.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._card_container.remove(child)
            child = next_child

        gfile = self._files[self._current_index]
        card = FileCard(gfile)
        card.connect_progress(self._update_progress)
        card.connect_swipe_left(self._do_trash)
        card.connect_swipe_right(self._do_organize_prompt)
        card.connect_swipe_down(lambda _gfile: self._do_skip())
        card.connect_swipe_later(lambda _gfile: self._do_later())
        self._card_container.append(card)

    def _advance(self):
        """No longer increments index; just shows whatever is next in the list."""
        self._update_counter()
        self._show_current_card()

    def _update_counter(self):
        remaining = len(self._files) - self._current_index
        total = len(self._files)
        if remaining > 0:
            self._counter_label.set_label(f"{self._current_index + 1} / {total}")
        self._counter_label.set_visible(remaining > 0)

    # ── Actions ─────────────────────────────────────────────────────

    def _on_trash_clicked(self, _btn):
        if self._current_index < len(self._files):
            self._do_trash(self._files[self._current_index])

    def _on_skip_clicked(self, _btn):
        if self._current_index < len(self._files):
            self._do_skip()

    def _on_later_clicked(self, _btn):
        if self._current_index < len(self._files):
            self._do_later()

    def _on_organize_clicked(self, _btn):
        if self._current_index < len(self._files):
            self._do_organize_prompt(self._files[self._current_index])

    def _do_skip(self):
        """Skip the current file without any action."""
        if self._current_index < len(self._files):
            self._files.pop(self._current_index)
            self._advance()

    def _do_later(self):
        """Re-queue the current file at the end of the list."""
        if self._current_index < len(self._files):
            gfile = self._files.pop(self._current_index)
            self._files.append(gfile)
            # Don't increment index — the next file shifted into this slot
            self._update_counter()
            self._show_current_card()

    def _do_trash(self, gfile: Gio.File):
        # If there's a pending trash, confirm it immediately
        if self._pending_trash:
            self._confirm_trash()
            if self._trash_toast:
                try:
                    self._trash_toast.dismiss()
                except:
                    pass

        # Pop from list so it disappears visually
        if self._current_index < len(self._files) and self._files[self._current_index] == gfile:
            self._files.pop(self._current_index)
        
        self._pending_trash = gfile
        
        filename = gfile.get_basename()
        self._trash_toast = Adw.Toast.new(f"Trashed '{filename}'")
        self._trash_toast.set_button_label("Undo")
        self._trash_toast.set_timeout(5)
        self._trash_toast.set_priority(Adw.ToastPriority.HIGH)
        
        # Connect signals
        self._trash_toast.connect("button-clicked", self._on_undo_trash_clicked)
        self._trash_toast.connect("dismissed", self._on_trash_toast_dismissed)
        
        self._toast_overlay.add_toast(self._trash_toast)
        self._advance()

    def _on_undo_trash_clicked(self, toast):
        self._cancel_trash()
        toast.dismiss()

    def _on_trash_toast_dismissed(self, toast):
        # Only confirm if this specific toast is still the one we're waiting for
        if self._pending_trash and toast == self._trash_toast:
            self._confirm_trash()

    def _cancel_trash(self):
        if self._pending_trash:
            # Re-insert the file at current position
            if self._current_index > len(self._files):
                self._current_index = len(self._files)
            self._files.insert(self._current_index, self._pending_trash)
            self._pending_trash = None
            self._trash_toast = None
            self._update_counter()
            self._show_current_card()

    def _confirm_trash(self):
        if self._pending_trash:
            filename = self._pending_trash.get_basename()
            ok = FileManager.trash(self._pending_trash)
            if not ok:
                toast = Adw.Toast.new(f"Failed to trash '{filename}'")
                self._toast_overlay.add_toast(toast)
            self._pending_trash = None

    def _do_organize_prompt(self, gfile: Gio.File):
        """Open file chooser."""
        self._pending_file = gfile
        self._refresh_recent_panel()
        # Also open the system file chooser dialog
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Choose Destination Folder")
        dialog.select_folder(self, None, self._on_dest_folder_selected)

    def _do_move_to(self, dest_path: str):
        if self._pending_file is None:
            return
        
        filename = self._pending_file.get_basename()
        ok = FileManager.move(self._pending_file, dest_path)
        
        if ok:
            self._recent.add(dest_path)
            self._refresh_recent_panel()
            # Pop from list on success
            if self._current_index < len(self._files) and self._files[self._current_index] == self._pending_file:
                self._files.pop(self._current_index)
            self._pending_file = None
            self._advance()
        else:
            # Show error toast
            toast = Adw.Toast.new(f"Failed to move '{filename}'")
            toast.set_priority(Adw.ToastPriority.HIGH)
            self._toast_overlay.add_toast(toast)
            self._pending_file = None
            # Don't advance on failure, let user try again or skip
            self._show_current_card()

    # ── Start/Done page recent folders ────────────────────────────

    def _build_start_recent_list(self):
        """Build recent source folders list for empty and done states."""
        # Empty page list
        self._empty_recent_box = self._create_recent_sources_box()
        self._empty_recent_listbox = self._empty_recent_box.listbox
        self._empty_page.append(self._empty_recent_box)

        # Done page list
        self._done_recent_box = self._create_recent_sources_box()
        self._done_recent_listbox = self._done_recent_box.listbox
        self._done_page.append(self._done_recent_box)

        self._refresh_start_recent_list()

    def _create_recent_sources_box(self):
        """Helper to create a box with a listbox for recent sources."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(8)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")
        box.append(listbox)
        box.listbox = listbox
        return box

    def _refresh_start_recent_list(self):
        """Refresh the recent source folders list on both empty and done pages."""
        for listbox in [self._empty_recent_listbox, self._done_recent_listbox]:
            while True:
                row = listbox.get_row_at_index(0)
                if row is None:
                    break
                listbox.remove(row)

        folders = self._recent_sources.get_all()
        visible = bool(folders)
        self._empty_recent_box.set_visible(visible)
        self._done_recent_box.set_visible(visible)

        if not visible:
            return

        for folder_path in folders:
            # We need separate rows for separate listboxes
            for listbox in [self._empty_recent_listbox, self._done_recent_listbox]:
                row = Adw.ActionRow(
                    title=Path(folder_path).name,
                    subtitle=folder_path,
                )
                
                icon_btn = Gtk.Button(icon_name="folder-symbolic")
                icon_btn.add_css_class("flat")
                icon_btn.set_valign(Gtk.Align.CENTER)
                icon_btn.set_tooltip_text("Open folder in file manager")
                icon_btn.connect("clicked", self._on_open_folder_clicked, folder_path)
                row.add_prefix(icon_btn)
                
                row.add_css_class("recent-row")
                row.set_activatable(True)
                row.connect("activated", self._on_start_recent_activated, folder_path)

                del_btn = Gtk.Button(icon_name="edit-delete-symbolic")
                del_btn.add_css_class("flat")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.set_tooltip_text("Remove from recents")
                del_btn.connect("clicked", self._on_start_recent_delete, folder_path)
                row.add_suffix(del_btn)

                listbox.append(row)

    def _on_start_recent_delete(self, _btn, folder_path):
        self._recent_sources.remove(folder_path)
        self._refresh_start_recent_list()

    def _on_start_recent_activated(self, _row, folder_path):
        self._source_dir = folder_path
        self._load_files(folder_path)

    # ── Recent folders panel (organize destination) ───────────────────

    def _build_recent_panel(self):
        self._recent_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._recent_frame.add_css_class("recent-panel")

        header_label = Gtk.Label(label="Move to…")
        header_label.add_css_class("recent-panel-header")
        header_label.add_css_class("dim-label")
        header_label.set_halign(Gtk.Align.START)
        self._recent_frame.append(header_label)

        self._recent_listbox = Gtk.ListBox()
        self._recent_listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._recent_listbox.add_css_class("boxed-list")
        self._recent_frame.append(self._recent_listbox)

        self._refresh_recent_panel()

    def _refresh_recent_panel(self):
        # Clear existing rows
        while True:
            row = self._recent_listbox.get_row_at_index(0)
            if row is None:
                break
            self._recent_listbox.remove(row)

        # Add recent folder rows
        folders = self._recent.get_all()
        for folder_path in folders:
            row = Adw.ActionRow(
                title=Path(folder_path).name,
                subtitle=folder_path,
            )
            # Add folder icon as clickable prefix
            icon_btn = Gtk.Button(icon_name="folder-symbolic")
            icon_btn.add_css_class("flat")
            icon_btn.set_valign(Gtk.Align.CENTER)
            icon_btn.set_tooltip_text("Open folder in file manager")
            icon_btn.connect("clicked", self._on_open_folder_clicked, folder_path)
            row.add_prefix(icon_btn)

            row.add_css_class("recent-row")
            row.set_activatable(True)

            # Remove button
            remove_btn = Gtk.Button(icon_name="window-close-symbolic")
            remove_btn.add_css_class("flat")
            remove_btn.set_valign(Gtk.Align.CENTER)
            remove_btn.connect("clicked", self._on_remove_recent, folder_path)
            row.add_suffix(remove_btn)

            # Click to select this folder
            row.connect("activated", self._on_recent_folder_activated, folder_path)
            self._recent_listbox.append(row)

        # "Choose folder…" row
        choose_row = Adw.ActionRow(
            title="Choose folder…",
        )
        choose_icon = Gtk.Image.new_from_icon_name("list-add-symbolic")
        choose_row.add_prefix(choose_icon)
        choose_row.set_activatable(True)
        choose_row.connect("activated", self._on_choose_folder)
        self._recent_listbox.append(choose_row)

    def _on_recent_folder_activated(self, _row, folder_path):
        if self._current_index >= len(self._files):
            return

        # If no file is pending (e.g. from an 'Organize' button click),
        # use the current file.
        if self._pending_file is None:
            self._pending_file = self._files[self._current_index]

        self._do_move_to(folder_path)

    def _on_remove_recent(self, _btn, folder_path):
        self._recent.remove(folder_path)
        self._refresh_recent_panel()

    def _on_choose_folder(self, _row):
        if self._current_index < len(self._files) and self._pending_file is None:
            self._pending_file = self._files[self._current_index]

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Choose Destination Folder")
        dialog.select_folder(self, None, self._on_dest_folder_selected)

    def _on_dest_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error:
            # User cancelled the dialog — cancel the organize
            self._pending_file = None
            self._show_current_card()
            return
        if folder is None:
            self._pending_file = None
            self._show_current_card()
            return
        
        path = folder.get_path()
        self._recent.add(path)
        self._refresh_recent_panel()
        self._do_move_to(path)

    # ── Shortcuts Dialog ───────────────────────────────────────────────

    def _on_shortcuts_clicked(self, _action, _param):
        def on_shortcut_changed():
            self._config.save()
            self._update_button_tooltips()

        dialog = ShortcutEditorDialog(self, self._config, on_shortcut_changed)
        dialog.present()



