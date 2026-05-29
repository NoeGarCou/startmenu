import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


def ask_name(parent, title: str, prompt: str, default: str = "") -> str | None:
    """
    Show a small modal dialog with a single text entry.
    Returns the trimmed text, or None if the user cancelled or left it empty.
    """
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
    entry.set_text(default)
    entry.set_activates_default(True)
    area.add(entry)

    dlg.show_all()
    response = dlg.run()
    text = entry.get_text().strip() if response == Gtk.ResponseType.OK else ""
    dlg.destroy()
    return text or None
