import subprocess

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def _run(cmd: list[str]) -> None:
    """Fire-and-forget process launch — does not block the UI."""
    subprocess.Popen(cmd)


class PowerStrip(Gtk.Box):
    """
    Narrow left column: settings gear at the top, power controls at the bottom.
    All buttons are icon-only with tooltips.
    """

    def __init__(self, *, on_prefs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("power-strip")

        self.pack_start(
            self._btn("preferences-system-symbolic", "Preferences", on_prefs),
            False, False, 0,
        )

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        self.pack_start(spacer, True, True, 0)

        for icon, tip, cmd in [
            ("system-lock-screen-symbolic", "Lock",     ["cinnamon-screensaver-command", "--lock"]),
            ("system-suspend-symbolic",     "Suspend",  ["systemctl", "suspend"]),
            ("system-reboot-symbolic",      "Restart",  ["systemctl", "reboot"]),
            ("system-shutdown-symbolic",    "Shut down",["systemctl", "poweroff"]),
        ]:
            self.pack_start(
                self._btn(icon, tip, lambda c=cmd: _run(c)),
                False, False, 0,
            )

    @staticmethod
    def _btn(icon: str, tooltip: str, callback) -> Gtk.Button:
        btn = Gtk.Button()
        btn.set_name("strip-btn")
        btn.set_relief(Gtk.ReliefStyle.NONE)
        btn.set_focus_on_click(False)
        btn.set_tooltip_text(tooltip)
        btn.add(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON))
        btn.connect("clicked", lambda _: callback())
        return btn
