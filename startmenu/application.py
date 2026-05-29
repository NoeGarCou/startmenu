import os

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gio

from .config import APP_ID
from .window import StartWindow


class StartApplication(Gtk.Application):
    """
    Single-instance GTK application.

    Normal invocation toggles the window.

    --pin <path> [<path> ...] invocation (from Nemo context menu or shell):
      Primary instance receives the paths and shows a section-picker dialog.
      If the app was not already running it starts, shows only the picker,
      then quits — it does NOT open the main window.
    """

    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self._window: StartWindow | None = None
        self._pending_pins: list[str] = []

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)

    def do_command_line(self, command_line) -> int:
        args = command_line.get_arguments()[1:]   # strip argv[0]
        if args and args[0] == "--pin":
            self._pending_pins = args[1:]
        self.activate()
        return 0

    def do_activate(self) -> None:
        if self._pending_pins:
            paths = list(self._pending_pins)
            self._pending_pins.clear()
            self._show_pin_picker(paths)
        elif self._window is None:
            self._window = StartWindow(application=self)
            self.add_window(self._window)
        else:
            self._window.toggle()

    # ── Section picker ────────────────────────────────────────────────

    def _show_pin_picker(self, paths: list[str]) -> None:
        from .pinned import pinned_data
        from .folder_info import make_id, make_file_id

        def _pin_to(section_id: str) -> None:
            for path in paths:
                app_id = make_id(path) if os.path.isdir(path) else make_file_id(path)
                pinned_data.pin(app_id, section_id)
            if self._window:
                self._window.refresh_pins()

        # No sections yet — prompt to create one first
        if not pinned_data.sections:
            name = _ask_name(None, "New Section",
                             "No sections yet.\nEnter a name for the first one:")
            if name:
                sec = pinned_data.add_section(name)
                _pin_to(sec.id)
            if self._window is None:
                self.quit()
            return

        # Single section — pin silently, no dialog needed
        if len(pinned_data.sections) == 1:
            _pin_to(pinned_data.sections[0].id)
            if self._window is None:
                self.quit()
            return

        # Multiple sections — show a picker
        no_window = self._window is None
        if no_window:
            self.hold()   # keep app alive while dialog is open

        win = self._window if (self._window and self._window.is_toplevel()) else None
        dlg = Gtk.Dialog(title="Pin to StartMenu", parent=win, modal=True,
                         destroy_with_parent=True)
        dlg.set_default_size(260, -1)

        area = dlg.get_content_area()
        area.set_spacing(6)
        area.set_margin_top(14)
        area.set_margin_bottom(8)
        area.set_margin_start(18)
        area.set_margin_end(18)

        noun = "item" if len(paths) == 1 else f"{len(paths)} items"
        area.add(Gtk.Label(label=f"Pin {noun} to:", halign=Gtk.Align.START))

        chosen = [None]
        for sec in pinned_data.sections:
            btn = Gtk.Button(label=sec.name)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            def _pick(_, s=sec):
                chosen[0] = s.id
                dlg.response(Gtk.ResponseType.OK)
            btn.connect("clicked", _pick)
            area.add(btn)

        dlg.add_button("_Cancel", Gtk.ResponseType.CANCEL)
        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK and chosen[0]:
            _pin_to(chosen[0])
        dlg.destroy()

        if no_window:
            self.release()   # allows app to quit if no windows remain


def _ask_name(parent, title: str, prompt: str) -> str | None:
    win = parent if (parent and parent.is_toplevel()) else None
    dlg = Gtk.Dialog(title=title, parent=win, modal=True, destroy_with_parent=True)
    dlg.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK)
    dlg.set_default_response(Gtk.ResponseType.OK)
    dlg.set_default_size(300, -1)
    area = dlg.get_content_area()
    area.set_spacing(8)
    area.set_margin_top(16)
    area.set_margin_bottom(8)
    area.set_margin_start(20)
    area.set_margin_end(20)
    area.add(Gtk.Label(label=prompt, halign=Gtk.Align.START))
    entry = Gtk.Entry()
    entry.set_activates_default(True)
    area.add(entry)
    dlg.show_all()
    text = entry.get_text().strip() if dlg.run() == Gtk.ResponseType.OK else ""
    dlg.destroy()
    return text or None
