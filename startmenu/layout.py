import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gio

from .app_source import load_apps
from .app_list import AppList
from .pinned_panel import PinnedPanel
from .power_strip import PowerStrip
from .settings import settings


class StartLayout(Gtk.Box):
    """
    Top-level layout widget.

    Horizontal arrangement:
      PowerStrip (narrow) | AppList (fixed width) | PinnedPanel (fills rest)
    """

    def __init__(self, *, on_launch, on_prefs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.set_name("start-container")

        apps = load_apps()
        app_map = {a.get_id(): a for a in apps if a.get_id()}

        self._pinned_panel = PinnedPanel(
            app_map,
            on_launch=on_launch,
            on_pin_changed=self._on_pin_changed,
        )
        self._app_list = AppList(
            apps,
            on_launch=on_launch,
            on_pin_changed=self._on_pin_changed,
        )
        power_strip = PowerStrip(on_prefs=on_prefs, on_refresh=self._on_apps_changed)

        self._app_list.set_size_request(settings.list_width, -1)
        # Prevent hexpand from propagating upward from child labels,
        # which would cause the list column to steal space from the pinned panel.
        self._app_list.set_hexpand(False)

        self.pack_start(power_strip,        False, False, 0)
        self.pack_start(self._app_list,     False, False, 0)
        self.pack_start(self._pinned_panel, True,  True,  0)

        # Reload the app list automatically when apps are installed or removed.
        self._app_monitor = Gio.AppInfoMonitor.get()
        self._app_monitor.connect("changed", self._on_apps_changed)

    # ── Public interface ──────────────────────────────────────────────

    def focus_search(self) -> None:
        self._app_list.focus_search()

    def reset(self) -> None:
        self._app_list.reset()

    def apply_settings(self) -> None:
        self._app_list.set_size_request(settings.list_width, -1)
        from .style import apply_size_css, apply_background_css, apply_border_css
        apply_background_css(settings)
        apply_border_css(settings)
        apply_size_css(settings)
        self._app_list.rebuild()
        self._pinned_panel.refresh()

    # ── Internal ──────────────────────────────────────────────────────

    def _on_pin_changed(self) -> None:
        self._pinned_panel.refresh()

    def _on_apps_changed(self, _monitor) -> None:
        apps = load_apps()
        self._pinned_panel._app_map = {a.get_id(): a for a in apps if a.get_id()}
        self._app_list.reload(apps)
