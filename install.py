#!/usr/bin/env python3
"""
StartMenu setup script — run once after installing the package.

    python3 setup.py

What it does:
  1. Creates ~/.local/share/applications/startmenu.desktop so StartMenu
     appears in the Cinnamon app menu and can be dragged to Plank.
  2. Creates a Nemo action so you can right-click any file or folder in
     the file manager and pin it to StartMenu.
"""

import shutil
import subprocess
from pathlib import Path

DESKTOP_DIR      = Path.home() / ".local" / "share" / "applications"
DESKTOP_FILE     = DESKTOP_DIR / "startmenu.desktop"
NEMO_ACTIONS_DIR = Path.home() / ".local" / "share" / "nemo" / "actions"
NEMO_ACTION_FILE = NEMO_ACTIONS_DIR / "pin-to-startmenu.nemo_action"


def _exec_cmd() -> str:
    """
    Return the command that launches StartMenu.

    Prefers the installed `startmenu` console-script (added to PATH by pip).
    Falls back to `python3 -m startmenu` run from this file's directory,
    which works when running straight from a cloned repo.
    """
    installed = shutil.which("startmenu")
    if installed:
        return installed
    # Running from source — use launch.sh so the module is on sys.path
    launch_sh = Path(__file__).resolve().parent / "launch.sh"
    if launch_sh.exists():
        launch_sh.chmod(launch_sh.stat().st_mode | 0o111)
        return str(launch_sh)
    return "python3 -m startmenu"


def create_desktop_file() -> None:
    print("── Creating .desktop file ────────────────────────────────────────")
    DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
    cmd = _exec_cmd()
    DESKTOP_FILE.write_text(
        "[Desktop Entry]\n"
        "Name=StartMenu\n"
        "Comment=App Launcher\n"
        f"Exec={cmd}\n"
        "Icon=applications-all\n"
        "Type=Application\n"
        "Categories=Utility;\n"
        "StartupNotify=false\n"
    )
    subprocess.run(["update-desktop-database", str(DESKTOP_DIR)], capture_output=True)
    print(f"  ✓ {DESKTOP_FILE}")
    print("  → Find 'StartMenu' in the Cinnamon app menu and drag it onto Plank.")


def create_nemo_action() -> None:
    print()
    print("── Creating Nemo action ──────────────────────────────────────────")
    NEMO_ACTIONS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = _exec_cmd()
    NEMO_ACTION_FILE.write_text(
        "[Nemo Action]\n"
        "Active=true\n"
        "Name=Pin to StartMenu\n"
        "Comment=Pin this file or folder to StartMenu\n"
        f"Exec={cmd} --pin %P\n"
        "Icon-Name=user-bookmarks\n"
        "Selection=any\n"
        "Extensions=any;\n"
    )
    print(f"  ✓ {NEMO_ACTION_FILE}")
    print("  → Right-click any file or folder in Nemo to pin it to StartMenu.")


def main() -> None:
    print()
    print("═══════════════════ StartMenu Setup ════════════════════")
    print()
    create_desktop_file()
    create_nemo_action()
    print()
    print("═══════════════════════ Done ═══════════════════════════")
    print()


if __name__ == "__main__":
    main()
