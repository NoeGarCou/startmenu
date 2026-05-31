"""
Persistent user settings for StartMenu.

Values are stored in ~/.config/startmenu/settings.json.
Import the module-level `settings` singleton and mutate it; call
settings.save() to persist changes to disk.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from pathlib import Path


_CONFIG_PATH  = os.path.expanduser("~/.config/startmenu/settings.json")
_DESKTOP_PATH = Path.home() / ".local/share/applications/startmenu.desktop"

# One-time migration: copy settings from the old pillmenu config dir if the
# new startmenu dir doesn't exist yet.
_OLD_CONFIG = os.path.expanduser("~/.config/pillmenu/settings.json")
if not os.path.exists(_CONFIG_PATH) and os.path.exists(_OLD_CONFIG):
    import shutil
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    shutil.copy2(_OLD_CONFIG, _CONFIG_PATH)

# Authoritative defaults — also used when a key is missing from the JSON file
# (forward-compatible: new keys added in the future won't break existing configs).
_DEFAULTS: dict = {
    "bottom_offset": 90,
    "window_width": 980,
    "window_height": 580,
    "hide_on_focus_loss": True,
    "dock_label": "Menu",
    "list_width": 265,
    "tile_icon_size": 48,
    "list_icon_size": 22,
    "tile_font_size": 11,
    "list_font_size": 13,
    "section_label_font_size": 10,
    "background_opacity": 0.97,
    "background_color": "#1c1c28",
    "border_width": 1,
    "border_color": "#ffffff",
    "border_alpha": 0.039,
    "anim_enabled": True,
    "anim_open_ms": 224,
    "anim_close_ms": 160,
    "anim_slide_px": 22,
}


@dataclass
class Settings:
    bottom_offset: int = 90
    window_width: int = 980
    window_height: int = 580
    hide_on_focus_loss: bool = True
    dock_label: str = "Menu"
    list_width: int = 265
    tile_icon_size: int = 48
    list_icon_size: int = 22
    tile_font_size: int = 11
    list_font_size: int = 13
    section_label_font_size: int = 10
    background_opacity: float = 0.97
    background_color: str = "#1c1c28"
    border_width: int = 1
    border_color: str = "#ffffff"
    border_alpha: float = 0.039
    anim_enabled: bool = True
    anim_open_ms: int = 224
    anim_close_ms: int = 160
    anim_slide_px: int = 22

    def save(self) -> None:
        os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
        with open(_CONFIG_PATH, "w") as fh:
            json.dump(asdict(self), fh, indent=2)

    def apply_dock_label(self) -> None:
        """Rewrite the Name= field in the installed .desktop file so Plank
        picks up the new tooltip on the next hover."""
        if not _DESKTOP_PATH.exists():
            return
        lines = _DESKTOP_PATH.read_text().splitlines()
        _DESKTOP_PATH.write_text(
            "\n".join(
                f"Name={self.dock_label}" if l.startswith("Name=") else l
                for l in lines
            ) + "\n"
        )

    @classmethod
    def load(cls) -> Settings:
        try:
            with open(_CONFIG_PATH) as fh:
                data = json.load(fh)
            # Only pick up known keys so stale/unknown entries are ignored
            merged = {**_DEFAULTS, **{k: v for k, v in data.items() if k in _DEFAULTS}}
            return cls(**merged)
        except (FileNotFoundError, json.JSONDecodeError, TypeError, KeyError):
            return cls()


# Module-level singleton.  Other modules do:  from .settings import settings
settings = Settings.load()
