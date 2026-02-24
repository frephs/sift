"""File operations: list, trash, move, and preview generation."""

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")

from gi.repository import Gio, GLib, GdkPixbuf
from pathlib import Path

# Thumbnail size for preview cards
PREVIEW_SIZE = 480

# File extensions that we can render as image previews directly
IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff", ".tif", ".ico",
}

# Extensions we treat as text-previewable (show icon + snippet later)
TEXT_EXTENSIONS = {
    ".txt", ".md", ".py", ".js", ".ts", ".c", ".cpp", ".h", ".rs", ".go",
    ".json", ".xml", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv",
    ".html", ".css", ".sh", ".bash", ".zsh",
}


class FileManager:
    """Stateless helpers that operate on Gio.File objects."""

    @staticmethod
    def list_files(directory_path: str) -> list[Gio.File]:
        """Return a sorted list of non-hidden Gio.File children."""
        gdir = Gio.File.new_for_path(directory_path)
        try:
            enumerator = gdir.enumerate_children(
                "standard::name,standard::type,standard::is-hidden",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
        except GLib.Error:
            return []

        files: list[Gio.File] = []
        while True:
            info = enumerator.next_file(None)
            if info is None:
                break
            if info.get_is_hidden():
                continue
            if info.get_file_type() == Gio.FileType.DIRECTORY:
                continue
            child = gdir.get_child(info.get_name())
            files.append(child)

        files.sort(key=lambda f: f.get_basename().lower())
        return files

    @staticmethod
    def trash(gfile: Gio.File) -> bool:
        """Move *gfile* to the GNOME Trash.  Returns True on success."""
        try:
            gfile.trash(None)
            return True
        except GLib.Error as e:
            print(f"Trash failed: {e.message}")
            return False

    @staticmethod
    def move(gfile: Gio.File, dest_dir_path: str) -> bool:
        """Move *gfile* into *dest_dir_path*.  Returns True on success."""
        dest_dir = Gio.File.new_for_path(dest_dir_path)
        dest = dest_dir.get_child(gfile.get_basename())
        try:
            gfile.move(dest, Gio.FileCopyFlags.NONE, None, None, None)
            return True
        except GLib.Error as e:
            print(f"Move failed: {e.message}")
            return False

    @staticmethod
    def get_file_info(gfile: Gio.File) -> dict:
        """Return a dict with name, size, content_type, modified time."""
        try:
            info = gfile.query_info(
                "standard::display-name,standard::size,standard::content-type,"
                "time::modified",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
            return {
                "name": info.get_display_name(),
                "size": info.get_size(),
                "content_type": info.get_content_type(),
                "modified": info.get_modification_date_time(),
            }
        except GLib.Error:
            return {
                "name": gfile.get_basename(),
                "size": 0,
                "content_type": "application/octet-stream",
                "modified": None,
            }

    @staticmethod
    def get_preview_pixbuf(gfile: Gio.File, size: int = PREVIEW_SIZE):
        """Return a GdkPixbuf.Pixbuf thumbnail, or None."""
        path = gfile.get_path()
        if path is None:
            return None
        ext = Path(path).suffix.lower()
        if ext in IMAGE_EXTENSIONS:
            try:
                return GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    path, size, size, True
                )
            except GLib.Error:
                return None
        return None

    @staticmethod
    def get_content_icon(content_type: str) -> Gio.Icon:
        """Return a Gio.Icon for a content type."""
        icon = Gio.content_type_get_icon(content_type)
        return icon

    @staticmethod
    def format_size(size_bytes: int) -> str:
        """Human-readable file size."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 ** 3:
            return f"{size_bytes / 1024**2:.1f} MB"
        else:
            return f"{size_bytes / 1024**3:.1f} GB"
