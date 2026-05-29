import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango

from .settings import settings


class AppItem(Gtk.FlowBoxChild):
    """
    A single app tile: icon on top, truncated name below.

    FlowBoxChild is a windowless widget and cannot receive pointer events
    directly. Hover / press state is managed by AppGrid at the FlowBox level
    using motion-notify-event + get_child_at_pos().
    """

    def __init__(self, app_info):
        super().__init__()
        self.app_info = app_info

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_size_request(80, 90)
        box.set_halign(Gtk.Align.CENTER)

        icon = app_info.get_icon()
        if icon:
            image = Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)
        else:
            image = Gtk.Image.new_from_icon_name(
                "application-x-executable", Gtk.IconSize.DIALOG
            )
        image.set_pixel_size(settings.tile_icon_size)

        label = Gtk.Label(label=app_info.get_display_name())
        label.get_style_context().add_class("app-label")
        label.set_max_width_chars(10)
        label.set_ellipsize(Pango.EllipsizeMode.END)
        label.set_justify(Gtk.Justification.CENTER)
        label.set_line_wrap(True)
        label.set_lines(2)

        box.pack_start(image, False, False, 0)
        box.pack_start(label, False, False, 0)
        self.add(box)
        self.show_all()
