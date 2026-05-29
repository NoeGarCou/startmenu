"""
Read the active Plank dock background color so StartMenu can match it.

Plank stores the theme name in GSettings under a per-dock path.
Theme files live in ~/.local/share/plank/themes/ or /usr/share/plank/themes/.
The relevant key is FillEndColor which is the dominant dock background color,
in Plank's R;;G;;B;;A format (A is 0-255).
"""
import subprocess
from pathlib import Path

_GSETTINGS_SCHEMA = "net.launchpad.plank.dock.settings"
_DOCK_PATH        = "/net/launchpad/plank/docks/dock1/"

_THEME_SEARCH = [
    Path.home() / ".local/share/plank/themes",
    Path("/usr/share/plank/themes"),
]

_FALLBACK = "rgba(28, 28, 40, 0.97)"


def _gsettings_get(schema_path: str, key: str) -> str | None:
    try:
        r = subprocess.run(
            ["gsettings", "get", f"{_GSETTINGS_SCHEMA}:{schema_path}", key],
            capture_output=True, text=True, timeout=2,
        )
        value = r.stdout.strip().strip("'\"")
        return value or None
    except Exception:
        return None


def _parse_plank_color(raw: str) -> tuple[int, int, int, float] | None:
    """Parse 'R;;G;;B;;A' (A = 0-255) → (r, g, b, alpha_0_1)."""
    parts = raw.split(";;")
    if len(parts) != 4:
        return None
    try:
        r, g, b, a = (int(p) for p in parts)
        return r, g, b, round(a / 255, 3)
    except ValueError:
        return None


def _read_theme_fill(theme_name: str) -> tuple[int, int, int, float] | None:
    for base in _THEME_SEARCH:
        theme_file = base / theme_name / "dock.theme"
        if not theme_file.exists():
            continue
        try:
            for line in theme_file.read_text().splitlines():
                if line.startswith("FillEndColor="):
                    return _parse_plank_color(line.split("=", 1)[1])
        except Exception:
            pass
    return None


def get_background_css(opacity: float | None = None) -> str:
    """
    Return a CSS rgba() string matching the active Plank dock background.
    Falls back to the default dark color if Plank isn't found or readable.
    Pass `opacity` to override just the alpha (0.0–1.0).
    """
    theme_name = _gsettings_get(_DOCK_PATH, "theme")
    if not theme_name:
        if opacity is not None:
            # patch the fallback alpha
            parts = _FALLBACK.rstrip(")").split(",")
            return f"rgba({parts[0].split('(')[1]},{parts[1]},{parts[2]}, {opacity:.2f})"
        return _FALLBACK

    color = _read_theme_fill(theme_name)
    if not color:
        if opacity is not None:
            parts = _FALLBACK.rstrip(")").split(",")
            return f"rgba({parts[0].split('(')[1]},{parts[1]},{parts[2]}, {opacity:.2f})"
        return _FALLBACK

    r, g, b, a = color
    alpha = opacity if opacity is not None else a
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"
