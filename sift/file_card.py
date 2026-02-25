"""Swipeable file preview card widget."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, GdkPixbuf, Gio, GLib, Pango

from .file_manager import FileManager


class FileCard(Gtk.Overlay):
    """A card-style widget showing a file preview that can be swiped.

    Uses Gtk.Overlay so swipe feedback labels float on top of the card content.
    The entire widget translates via margins during a drag gesture.
    """

    SWIPE_THRESHOLD = 120  # px to trigger action
    MAX_ROTATION = 15     
      # degrees tilt at max drag
    SCROLL_THRESHOLD = 150  # accumulated scroll units to trigger action
    SCROLL_DEADZONE = 50    # scroll units below which no feedback shows
    SCROLL_PX_SCALE = 1.5   # multiplier: scroll units → pixel offset

    def __init__(self, gfile: Gio.File, **kwargs):
        super().__init__(**kwargs)
        self.gfile = gfile
        self._drag_x = 0.0
        self._drag_y = 0.0
        self._committed = False

        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)

        info = FileManager.get_file_info(gfile)

        # ── Main card content (child of the overlay) ────────────────
        card_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=0,
        )
        card_box.add_css_class("file-card")
        card_box.set_overflow(Gtk.Overflow.HIDDEN)

        # --- Preview area ---
        preview_frame = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            hexpand=True,
            vexpand=True,
        )
        preview_frame.add_css_class("file-card-preview")

        pixbuf = FileManager.get_preview_pixbuf(gfile)
        if pixbuf is not None:
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            picture = Gtk.Picture.new_for_paintable(texture)
            picture.set_content_fit(Gtk.ContentFit.CONTAIN)
            picture.set_hexpand(True)
            picture.set_vexpand(True)
            preview_frame.append(picture)
        else:
            # Icon fallback
            icon_box = Gtk.Box(
                orientation=Gtk.Orientation.VERTICAL,
                halign=Gtk.Align.CENTER,
                valign=Gtk.Align.CENTER,
                vexpand=True,
                spacing=12,
            )
            content_icon = FileManager.get_content_icon(info["content_type"])
            icon_image = Gtk.Image.new_from_gicon(content_icon)
            icon_image.set_pixel_size(96)
            icon_image.add_css_class("dim-label")
            icon_box.append(icon_image)

            ext_label = Gtk.Label(
                label=self._get_extension(info["name"]).upper() or "FILE"
            )
            ext_label.add_css_class("title-3")
            ext_label.add_css_class("dim-label")
            icon_box.append(ext_label)

            preview_frame.append(icon_box)

        card_box.append(preview_frame)

        # Info bar
        info_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=4,
        )
        info_box.add_css_class("file-card-info")
        info_box.set_can_focus(True)
        info_box.update_property([Gtk.AccessibleProperty.LABEL], [f"File: {info['name']}"])

        name_label = Gtk.Label(label=info["name"])
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        name_label.set_max_width_chars(30)
        name_label.add_css_class("title-4")
        name_label.set_halign(Gtk.Align.START)
        info_box.append(name_label)

        meta_parts = []
        meta_parts.append(FileManager.format_size(info["size"]))
        if info["content_type"]:
            desc = Gio.content_type_get_description(info["content_type"])
            if desc:
                meta_parts.append(desc)

        meta_label = Gtk.Label(label=" · ".join(meta_parts))
        meta_label.add_css_class("caption")
        meta_label.add_css_class("dim-label")
        meta_label.set_halign(Gtk.Align.START)
        meta_label.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.append(meta_label)

        card_box.append(info_box)

        # Set the card box as the main child of the overlay
        self.set_child(card_box)
        self._card_box = card_box

        # ── Swipe overlay labels (float on top) ─────────────────────
        self._trash_label = self._create_overlay_box("user-trash-symbolic", "TRASH", "swipe-label-trash")
        self._trash_label.set_halign(Gtk.Align.START)
        self._trash_label.set_valign(Gtk.Align.START)
        self.add_overlay(self._trash_label)

        self._organize_label = self._create_overlay_box("folder-symbolic", "ORGANIZE", "swipe-label-organize")
        self._organize_label.set_halign(Gtk.Align.END)
        self._organize_label.set_valign(Gtk.Align.START)
        self.add_overlay(self._organize_label)

        self._skip_label = self._create_overlay_box("go-next-symbolic", "SKIP", "swipe-label-skip")
        self._skip_label.set_halign(Gtk.Align.CENTER)
        self._skip_label.set_valign(Gtk.Align.START)
        self.add_overlay(self._skip_label)

        self._later_label = self._create_overlay_box("alarm-symbolic", "LATER", "swipe-label-later")
        self._later_label.set_halign(Gtk.Align.CENTER)
        self._later_label.set_valign(Gtk.Align.END)
        self.add_overlay(self._later_label)

        # Callbacks for swipe outcomes
        self._on_swipe_left = None   # trash callback
        self._on_swipe_right = None  # organize callback
        self._on_swipe_down = None   # skip callback
        self._on_swipe_later = None  # later callback
        self._on_progress_callback = None # progress update callback

        # ── Drag gesture ────────────────────────────────────────────
        drag = Gtk.GestureDrag.new()
        drag.connect("drag-begin", self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end", self._on_drag_end)
        self.add_controller(drag)

        # ── Scroll controller ───────────────────────────────────────
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES
        )
        scroll.connect("scroll-begin", self._on_scroll_begin)
        scroll.connect("scroll", self._on_scroll)
        scroll.connect("scroll-end", self._on_scroll_end)
        self.add_controller(scroll)
        self._scroll_dx = 0.0
        self._scroll_dy = 0.0
        self._scroll_committed = False

        # Callbacks for swipe outcomes
        self._on_swipe_left = None   # trash callback
        self._on_swipe_right = None  # organize callback
        self._on_swipe_down = None   # skip callback
        self._on_swipe_later = None  # later callback

    # -- public ---------------------------------------------------------------

    def _create_overlay_box(self, icon_name: str, text: str, css_class: str) -> Gtk.Box:
        """Create a styled box with an icon and label for swipe feedback."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.add_css_class(css_class)
        box.set_opacity(0)

        icon = Gtk.Image.new_from_icon_name(icon_name)
        box.append(icon)

        label = Gtk.Label(label=text)
        box.append(label)

        return box

    def connect_swipe_left(self, callback):
        self._on_swipe_left = callback

    def connect_swipe_right(self, callback):
        self._on_swipe_right = callback

    def connect_swipe_down(self, callback):
        self._on_swipe_down = callback

    def connect_swipe_later(self, callback):
        self._on_swipe_later = callback

    def connect_progress(self, callback):
        self._on_progress_callback = callback

    # -- internals ------------------------------------------------------------

    @staticmethod
    def _get_extension(filename: str) -> str:
        if "." in filename:
            return filename.rsplit(".", 1)[-1]
        return ""

    # -- scroll handling ------------------------------------------------------

    def _on_scroll_begin(self, controller):
        self._scroll_dx = 0.0
        self._scroll_dy = 0.0
        self._scroll_committed = False

    def _on_scroll(self, controller, dx, dy):
        if self._scroll_committed:
            return Gdk.EVENT_STOP

        # Adjust sensitivity for mouse wheel vs touchpad
        event = controller.get_current_event()
        if event and hasattr(event, "get_scroll_unit"):
            unit = event.get_scroll_unit()
            if unit == Gdk.ScrollUnit.WHEEL:
                # Mouse wheel often returns 1.0 per click.
                # If 150 is the threshold, we want it to be less 'sensible'.
                # We'll scale it so one click is around 30-40 units.
                dx *= 1000.0
                dy *= 1000.0
            elif unit == Gdk.ScrollUnit.SURFACE:
                # Touchpad / Smooth scroll - usually returns pixels.
                # Leave as is or apply a smaller factor.
                pass

        self._scroll_dx -= dx
        self._scroll_dy -= dy

        # Reset visual feedback
        self._trash_label.set_opacity(0)
        self._organize_label.set_opacity(0)
        self._skip_label.set_opacity(0)
        self._later_label.set_opacity(0)
        self._card_box.remove_css_class("swiping-left")
        self._card_box.remove_css_class("swiping-right")
        self._card_box.remove_css_class("swiping-up")
        self._card_box.remove_css_class("swiping-down")

        if self._on_progress_callback:
            self._on_progress_callback(None, 0.0)

        # Determine dominant axis magnitude
        adx = abs(self._scroll_dx)
        ady = abs(self._scroll_dy)
        dominant = max(adx, ady)

        # Dead zone: no feedback if scroll is too small
        if dominant < self.SCROLL_DEADZONE:
            return Gdk.EVENT_STOP

        fade_range = self.SCROLL_THRESHOLD - self.SCROLL_DEADZONE
        width = self.get_allocated_width()
        height = self.get_allocated_height()

        # Cross-gate logic: only show label if other axis is in deadzone
        if adx > ady and adx > self.SCROLL_DEADZONE and ady < self.SCROLL_DEADZONE:
            progress = min((adx - self.SCROLL_DEADZONE) / fade_range, 1.0)
            if self._scroll_dx < 0:
                self._trash_label.set_opacity(progress)
                self._card_box.add_css_class("swiping-left")
                if self._on_progress_callback:
                    self._on_progress_callback("trash", progress)
            else:
                self._organize_label.set_opacity(progress)
                self._card_box.add_css_class("swiping-right")
                if self._on_progress_callback:
                    self._on_progress_callback("organize", progress)
        elif ady > adx and ady > self.SCROLL_DEADZONE and adx < self.SCROLL_DEADZONE:
            progress = min((ady - self.SCROLL_DEADZONE) / fade_range, 1.0)
            if self._scroll_dy < 0:
                self._skip_label.set_opacity(progress)
                self._card_box.add_css_class("swiping-up")
                if self._on_progress_callback:
                    self._on_progress_callback("skip", progress)
            else:
                self._later_label.set_opacity(progress)
                self._card_box.add_css_class("swiping-down")
                if self._on_progress_callback:
                    self._on_progress_callback("later", progress)

        return Gdk.EVENT_STOP

    def _on_scroll_end(self, controller):
        if self._scroll_committed:
            return

        # Check threshold on release and trigger action
        if abs(self._scroll_dx) > abs(self._scroll_dy):
            if self._scroll_dx < -self.SCROLL_THRESHOLD:
                self._scroll_committed = True
                self._animate_exit("left")
                return
            elif self._scroll_dx > self.SCROLL_THRESHOLD:
                self._scroll_committed = True
                self._animate_exit("right")
                return
        else:
            if self._scroll_dy < -self.SCROLL_THRESHOLD:
                self._scroll_committed = True
                self._animate_exit("up")
                return
            elif self._scroll_dy > self.SCROLL_THRESHOLD:
                self._scroll_committed = True
                self._animate_exit("down")
                return

        # Threshold not met — reset
        self._reset_position()

    def _on_drag_begin(self, gesture, start_x, start_y):
        self._drag_x = 0
        self._drag_y = 0
        self._committed = False

    def _on_drag_update(self, gesture, offset_x, offset_y):
        self._drag_x = offset_x
        self._drag_y = offset_y

        # Determine dominant drag axis
        is_vertical_up = abs(offset_y) > abs(offset_x) and offset_y < 0
        is_vertical_down = abs(offset_y) > abs(offset_x) and offset_y > 0

        # Compute visual feedback intensity (0 → 1)
        if is_vertical_up or is_vertical_down:
            progress = min(abs(offset_y) / self.SWIPE_THRESHOLD, 1.0)
        else:
            progress = min(abs(offset_x) / self.SWIPE_THRESHOLD, 1.0)

        # Show appropriate overlay label
        self._trash_label.set_opacity(0)
        self._organize_label.set_opacity(0)
        self._skip_label.set_opacity(0)
        self._later_label.set_opacity(0)
        if is_vertical_up:
            self._skip_label.set_opacity(progress)
            if self._on_progress_callback:
                self._on_progress_callback("skip", progress)
        elif is_vertical_down:
            self._later_label.set_opacity(progress)
            if self._on_progress_callback:
                self._on_progress_callback("later", progress)
        elif offset_x < 0:
            self._trash_label.set_opacity(progress)
            if self._on_progress_callback:
                self._on_progress_callback("trash", progress)
        else:
            self._organize_label.set_opacity(progress)
            if self._on_progress_callback:
                self._on_progress_callback("organize", progress)

        # Apply CSS tint classes on the inner card box
        self._card_box.remove_css_class("swiping-left")
        self._card_box.remove_css_class("swiping-right")
        self._card_box.remove_css_class("swiping-up")
        self._card_box.remove_css_class("swiping-down")
        if is_vertical_up and offset_y < -20:
            self._card_box.add_css_class("swiping-up")
        elif is_vertical_down and offset_y > 20:
            self._card_box.add_css_class("swiping-down")
        elif offset_x < -20:
            self._card_box.add_css_class("swiping-left")
        elif offset_x > 20:
            self._card_box.add_css_class("swiping-right")

    def _on_drag_end(self, gesture, offset_x, offset_y):
        if self._committed:
            return

        is_vertical_up = abs(self._drag_y) > abs(self._drag_x) and self._drag_y < 0
        is_vertical_down = abs(self._drag_y) > abs(self._drag_x) and self._drag_y > 0

        if is_vertical_up and self._drag_y < -self.SWIPE_THRESHOLD:
            self._committed = True
            self._animate_exit("up")
        elif is_vertical_down and self._drag_y > self.SWIPE_THRESHOLD:
            self._committed = True
            self._animate_exit("down")
        elif self._drag_x < -self.SWIPE_THRESHOLD:
            self._committed = True
            self._animate_exit("left")
        elif self._drag_x > self.SWIPE_THRESHOLD:
            self._committed = True
            self._animate_exit("right")
        else:
            self._reset_position()

    def _reset_position(self):
        self.set_margin_start(0)
        self.set_margin_end(0)
        self.set_margin_top(0)
        self._trash_label.set_opacity(0)
        self._organize_label.set_opacity(0)
        self._skip_label.set_opacity(0)
        self._later_label.set_opacity(0)
        self._card_box.remove_css_class("swiping-left")
        self._card_box.remove_css_class("swiping-right")
        self._card_box.remove_css_class("swiping-up")
        self._card_box.remove_css_class("swiping-down")
        if self._on_progress_callback:
            self._on_progress_callback(None, 0.0)

    def _animate_exit(self, direction: str):
        """Animate the card out then fire the callback."""
        steps = 12
        current_step = [0]

        if direction == "left":
            self._card_box.add_css_class("exit-left")
        elif direction == "right":
            self._card_box.add_css_class("exit-right")
        elif direction == "up":
            self._card_box.add_css_class("exit-up")
        else:
            self._card_box.add_css_class("exit-down")

        def tick():
            current_step[0] += 1
            progress = current_step[0] / steps
            # Ease-out cubic
            eased = 1 - (1 - progress) ** 3

            self.set_opacity(1 - eased)

            if current_step[0] >= steps:
                if direction == "left" and self._on_swipe_left:
                    self._on_swipe_left(self.gfile)
                elif direction == "right" and self._on_swipe_right:
                    self._on_swipe_right(self.gfile)
                elif direction == "up" and self._on_swipe_down:
                    self._on_swipe_down(self.gfile)
                elif direction == "down" and self._on_swipe_later:
                    self._on_swipe_later(self.gfile)
                return GLib.SOURCE_REMOVE
            return GLib.SOURCE_CONTINUE

        GLib.timeout_add(16, tick)  # ~60 fps
