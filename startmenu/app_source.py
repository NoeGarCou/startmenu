import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio


def load_apps() -> list:
    """
    Return all visible installed apps sorted alphabetically by display name.

    Gio handles locale-aware names, NoDisplay/OnlyShowIn filtering, and
    icon resolution — do not hand-parse .desktop files.

    Deduplication: some installers (e.g. Wine app launchers) register two
    .desktop files with identical Name= and Exec= lines. We keep only the
    first entry per commandline so duplicates never reach the UI.
    """
    seen: set[str] = set()
    apps = []
    for a in Gio.AppInfo.get_all():
        if not a.should_show():
            continue
        key = a.get_commandline() or a.get_executable() or a.get_id() or ""
        if key in seen:
            continue
        seen.add(key)
        apps.append(a)
    return sorted(apps, key=lambda a: a.get_display_name().casefold())


def matches_query(app_info, query: str) -> bool:
    """Case-insensitive substring match against the app's display name."""
    return query.casefold() in app_info.get_display_name().casefold()
