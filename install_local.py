#!/usr/bin/env python3
import os
from pathlib import Path

APP_ID = "io.github.frephs.Sift"
PREFIX = Path.home() / ".local/share"
REPO_ROOT = Path(__file__).resolve().parent

# 1. Create the .desktop file
desktop_content = f"""[Desktop Entry]
Name=Sift
Exec=python3 {REPO_ROOT}/sift/main.py
Icon={REPO_ROOT}/sift/resources/io.github.frephs.Sift.svg
Terminal=false
Type=Application
Categories=Utility;GNOME;GTK;
StartupWMClass={APP_ID}
"""

desktop_path = PREFIX / "applications" / f"{APP_ID}.desktop"
desktop_path.parent.mkdir(parents=True, exist_ok=True)

with open(desktop_path, "w") as f:
    f.write(desktop_content)

# 2. Update desktop database
os.system(f"update-desktop-database {PREFIX / 'applications'}")

print(f"✅ Registered {APP_ID} locally.")
print(f"You can now find 'Sift' in your Activities overview.")
