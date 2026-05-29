# StartMenu

A lightweight application launcher for **Linux Mint Cinnamon**. Opens as a floating bottom-center window with a searchable app list and a pinned tiles panel — think Windows Start Menu, dark themed to match a Plank dock setup.

![screenshot placeholder]

## Features

- Searchable list of all installed apps
- Pinned tiles panel with drag-and-drop reordering
- Pin apps, folders, and files as tiles
- Right-click any file or folder in Nemo to pin it
- Single-instance toggle — one hotkey opens and closes it
- Dark themed with rounded corners, configurable via Preferences
- Animates in/out from the bottom of the screen

## Requirements

- Linux Mint (Cinnamon) or any GTK3 / X11 desktop
- Python 3.10+
- GTK3 Python bindings (system packages — not available via pip):

```bash
sudo apt install python3-gi python3-gi-cairo \
                 gir1.2-gtk-3.0 gir1.2-gdk-3.0 \
                 gir1.2-gio-2.0 gir1.2-gdkpixbuf-2.0
```

## Installation

### From GitHub (recommended)

```bash
# 1. Install system dependencies (including pip, which Mint omits by default)
sudo apt install python3-pip python3-gi python3-gi-cairo \
                 gir1.2-gtk-3.0 gir1.2-gdk-3.0 \
                 gir1.2-gio-2.0 gir1.2-gdkpixbuf-2.0

# 2. Install the package
# (--break-system-packages is required on Ubuntu 24.04+; safe with --user)
pip3 install --user --break-system-packages git+https://github.com/NoeGarCou/startmenu.git

# 3. Make sure ~/.local/bin is in PATH (needed if this is a fresh terminal)
source ~/.profile

# 4. Set up desktop integration (Plank launcher + Nemo context menu)
startmenu-setup
```

### From source (editable install — git pull updates immediately)

```bash
git clone https://github.com/NoeGarCou/startmenu.git
cd startmenu

sudo apt install python3-pip python3-gi python3-gi-cairo \
                 gir1.2-gtk-3.0 gir1.2-gdk-3.0 \
                 gir1.2-gio-2.0 gir1.2-gdkpixbuf-2.0

pip3 install --user --break-system-packages -e .
source ~/.profile
startmenu-setup
```

The `-e` flag installs in editable mode — `git pull` picks up changes immediately with no reinstall.

## First run

```bash
startmenu
```

Or trigger it from the Plank icon / your configured hotkey.

## Setting up a hotkey

In Cinnamon: **System Settings → Keyboard → Shortcuts → Custom Shortcuts → Add**.  
Set the command to `startmenu` and bind it to any key you like.

## Nemo context menu

After running `python3 install.py`, right-clicking any file or folder in the Nemo file manager shows **"Pin to StartMenu"**. If StartMenu is already running, the pin happens instantly. If it's not running, a small section-picker dialog appears and then the process exits.

## Configuration

All settings live in `~/.config/startmenu/settings.json` and are editable via the gear icon inside the launcher. Pinned items are stored in `~/.config/startmenu/pinned.json`.

## Updating

```bash
pip3 install --user --break-system-packages --upgrade git+https://github.com/NoeGarCou/startmenu.git
```
