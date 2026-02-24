"""Persistent application configuration and history."""

import json
import os
from pathlib import Path
from gi.repository import Gdk

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "gnome-sift"
CONFIG_FILE = CONFIG_DIR / "config.json"
MAX_RECENT = 10

DEFAULT_SHORTCUTS = {
    "trash": Gdk.KEY_Left,
    "organize": Gdk.KEY_Right,
    "skip": Gdk.KEY_Down,
    "later": Gdk.KEY_Up
}

SHORTCUT_NAMES = {
    "trash": "Trash",
    "organize": "Organize",
    "skip": "Skip",
    "later": "Later"
}

class Config:
    def __init__(self):
        self.shortcuts = DEFAULT_SHORTCUTS.copy()
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                if "shortcuts" in data:
                    for k, v in data["shortcuts"].items():
                        if k in self.shortcuts:
                            self.shortcuts[k] = v
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"shortcuts": self.shortcuts}, f, indent=2)
        except OSError:
            pass

    def get_shortcut_label(self, action: str) -> str:
        keyval = self.shortcuts.get(action)
        if keyval is None:
            return "None"
        name = Gdk.keyval_name(keyval)
        if not name:
            return str(keyval)
        mapping = {
            "Left": "←",
            "Right": "→",
            "Up": "↑",
            "Down": "↓",
            "Delete": "Del",
            "Return": "Enter",
            "Escape": "Esc",
            "space": "Space"
        }
        return mapping.get(name, name.capitalize())


class RecentFolders:
    """Read / write a small JSON list of folder paths."""

    def __init__(self, filename: str = "recent_folders.json"):
        self._config_file = CONFIG_DIR / filename
        self._folders: list[str] = []
        self._load()

    def get_all(self) -> list[str]:
        return list(self._folders)

    def add(self, path: str) -> None:
        path = str(Path(path).resolve())
        if path in self._folders:
            self._folders.remove(path)
        self._folders.insert(0, path)
        self._folders = self._folders[:MAX_RECENT]
        self._save()

    def remove(self, path: str) -> None:
        path = str(Path(path).resolve())
        if path in self._folders:
            self._folders.remove(path)
            self._save()

    def _load(self) -> None:
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._folders = [str(p) for p in data][:MAX_RECENT]
            except (json.JSONDecodeError, OSError):
                self._folders = []

    def _save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(self._config_file, "w") as f:
            json.dump(self._folders, f, indent=2)
