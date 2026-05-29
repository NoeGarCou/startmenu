import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

from .settings import settings


class PreferencesDialog(Gtk.Dialog):
    """
    Modal settings dialog with tabbed sections so it never overflows the screen.

    On Gtk.ResponseType.APPLY values are written to the `settings` singleton
    and persisted to disk.  The caller (StartWindow) applies live updates.
    """

    def __init__(self, parent: Gtk.Window):
        super().__init__(
            title="StartMenu Preferences",
            parent=parent,
            modal=True,
            destroy_with_parent=True,
        )
        self.set_default_size(420, -1)
        self.set_resizable(False)
        self.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Apply",  Gtk.ResponseType.APPLY,
        )
        self.set_default_response(Gtk.ResponseType.APPLY)

        area = self.get_content_area()
        area.set_margin_top(12)
        area.set_margin_bottom(8)
        area.set_margin_start(16)
        area.set_margin_end(16)

        nb = Gtk.Notebook()
        nb.set_tab_pos(Gtk.PositionType.TOP)
        area.add(nb)

        nb.append_page(self._build_window_tab(),     Gtk.Label(label="Window"))
        nb.append_page(self._build_appearance_tab(), Gtk.Label(label="Appearance"))
        nb.append_page(self._build_sizes_tab(),      Gtk.Label(label="Sizes"))
        nb.append_page(self._build_animation_tab(),  Gtk.Label(label="Animation"))

        self.connect("response", self._on_response)
        self.show_all()

    # ── Tab builders ──────────────────────────────────────────────────

    def _build_window_tab(self) -> Gtk.Widget:
        g = self._grid()

        g.attach(self._lbl("Bottom offset (px)"), 0, 0, 1, 1)
        self._spin_offset = Gtk.SpinButton.new_with_range(0, 400, 1)
        self._spin_offset.set_value(settings.bottom_offset)
        self._spin_offset.set_tooltip_text(
            "Distance from the bottom of the screen to the launcher's lower edge."
        )
        g.attach(self._spin_offset, 1, 0, 1, 1)

        g.attach(self._lbl("Window width (px)"), 0, 1, 1, 1)
        self._spin_width = Gtk.SpinButton.new_with_range(300, 1600, 10)
        self._spin_width.set_value(settings.window_width)
        g.attach(self._spin_width, 1, 1, 1, 1)

        g.attach(self._lbl("Window height (px)"), 0, 2, 1, 1)
        self._spin_height = Gtk.SpinButton.new_with_range(200, 1200, 10)
        self._spin_height.set_value(settings.window_height)
        g.attach(self._spin_height, 1, 2, 1, 1)

        g.attach(self._lbl("List column width (px)"), 0, 3, 1, 1)
        self._spin_list_width = Gtk.SpinButton.new_with_range(150, 500, 10)
        self._spin_list_width.set_value(settings.list_width)
        g.attach(self._spin_list_width, 1, 3, 1, 1)

        g.attach(self._lbl("Hide on focus loss"), 0, 4, 1, 1)
        self._switch_focus = Gtk.Switch()
        self._switch_focus.set_active(settings.hide_on_focus_loss)
        self._switch_focus.set_halign(Gtk.Align.START)
        self._switch_focus.set_tooltip_text(
            "Hide the launcher when you click outside it."
        )
        g.attach(self._switch_focus, 1, 4, 1, 1)

        g.attach(self._lbl("Dock label"), 0, 5, 1, 1)
        self._entry_label = Gtk.Entry()
        self._entry_label.set_text(settings.dock_label)
        self._entry_label.set_tooltip_text(
            "Tooltip shown when hovering the Plank icon. Takes effect after restarting Plank."
        )
        g.attach(self._entry_label, 1, 5, 1, 1)

        return self._tab_wrap(g)

    def _build_appearance_tab(self) -> Gtk.Widget:
        g = self._grid()

        g.attach(self._lbl("Background colour"), 0, 0, 1, 1)
        self._color_btn = Gtk.ColorButton()
        self._color_btn.set_use_alpha(False)
        self._color_btn.set_tooltip_text(
            "Base colour of the menu background (opacity is set separately)."
        )
        rgba = Gdk.RGBA()
        rgba.parse(settings.background_color)
        self._color_btn.set_rgba(rgba)
        g.attach(self._color_btn, 1, 0, 1, 1)

        g.attach(self._lbl("Background opacity"), 0, 1, 1, 1)
        self._scale_opacity = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.10, 1.0, 0.05
        )
        self._scale_opacity.set_value(settings.background_opacity)
        self._scale_opacity.set_hexpand(True)
        self._scale_opacity.set_draw_value(True)
        self._scale_opacity.set_digits(2)
        self._scale_opacity.set_tooltip_text(
            "Alpha of the menu background. Lower = more transparent."
        )
        g.attach(self._scale_opacity, 1, 1, 1, 1)

        return self._tab_wrap(g)

    def _build_sizes_tab(self) -> Gtk.Widget:
        g = self._grid()

        g.attach(self._lbl("Tile icon size (px)"), 0, 0, 1, 1)
        self._spin_tile_icon = Gtk.SpinButton.new_with_range(16, 128, 2)
        self._spin_tile_icon.set_value(settings.tile_icon_size)
        self._spin_tile_icon.set_tooltip_text("Icon size in the pinned-apps tile grid.")
        g.attach(self._spin_tile_icon, 1, 0, 1, 1)

        g.attach(self._lbl("Tile font size (px)"), 0, 1, 1, 1)
        self._spin_tile_font = Gtk.SpinButton.new_with_range(8, 24, 1)
        self._spin_tile_font.set_value(settings.tile_font_size)
        self._spin_tile_font.set_tooltip_text("Label font size below each tile icon.")
        g.attach(self._spin_tile_font, 1, 1, 1, 1)

        g.attach(self._lbl("List icon size (px)"), 0, 2, 1, 1)
        self._spin_list_icon = Gtk.SpinButton.new_with_range(12, 64, 2)
        self._spin_list_icon.set_value(settings.list_icon_size)
        self._spin_list_icon.set_tooltip_text("Icon size in the alphabetical app list.")
        g.attach(self._spin_list_icon, 1, 2, 1, 1)

        g.attach(self._lbl("List font size (px)"), 0, 3, 1, 1)
        self._spin_list_font = Gtk.SpinButton.new_with_range(8, 24, 1)
        self._spin_list_font.set_value(settings.list_font_size)
        self._spin_list_font.set_tooltip_text("Font size for app names in the list.")
        g.attach(self._spin_list_font, 1, 3, 1, 1)

        g.attach(self._lbl("Section label font size (px)"), 0, 4, 1, 1)
        self._spin_section_font = Gtk.SpinButton.new_with_range(8, 24, 1)
        self._spin_section_font.set_value(settings.section_label_font_size)
        self._spin_section_font.set_tooltip_text("Font size for section heading labels in the pinned panel.")
        g.attach(self._spin_section_font, 1, 4, 1, 1)

        return self._tab_wrap(g)

    def _build_animation_tab(self) -> Gtk.Widget:
        g = self._grid()

        g.attach(self._lbl("Enable animation"), 0, 0, 1, 1)
        self._switch_anim = Gtk.Switch()
        self._switch_anim.set_active(settings.anim_enabled)
        self._switch_anim.set_halign(Gtk.Align.START)
        g.attach(self._switch_anim, 1, 0, 1, 1)

        g.attach(self._lbl("Open duration (ms)"), 0, 1, 1, 1)
        self._spin_open_ms = Gtk.SpinButton.new_with_range(50, 1000, 10)
        self._spin_open_ms.set_value(settings.anim_open_ms)
        self._spin_open_ms.set_tooltip_text("How long the open animation takes.")
        g.attach(self._spin_open_ms, 1, 1, 1, 1)

        g.attach(self._lbl("Close duration (ms)"), 0, 2, 1, 1)
        self._spin_close_ms = Gtk.SpinButton.new_with_range(50, 1000, 10)
        self._spin_close_ms.set_value(settings.anim_close_ms)
        self._spin_close_ms.set_tooltip_text("How long the close animation takes.")
        g.attach(self._spin_close_ms, 1, 2, 1, 1)

        g.attach(self._lbl("Slide distance (px)"), 0, 3, 1, 1)
        self._spin_slide = Gtk.SpinButton.new_with_range(0, 120, 1)
        self._spin_slide.set_value(settings.anim_slide_px)
        self._spin_slide.set_tooltip_text(
            "How far the window rises on open / falls on close. 0 = fade only."
        )
        g.attach(self._spin_slide, 1, 3, 1, 1)

        return self._tab_wrap(g)

    # ── Widget helpers ────────────────────────────────────────────────

    @staticmethod
    def _grid() -> Gtk.Grid:
        g = Gtk.Grid()
        g.set_row_spacing(14)
        g.set_column_spacing(20)
        return g

    @staticmethod
    def _tab_wrap(widget: Gtk.Widget) -> Gtk.Widget:
        """Add consistent padding around each tab's content grid."""
        box = Gtk.Box()
        box.set_margin_top(18)
        box.set_margin_bottom(14)
        box.set_margin_start(20)
        box.set_margin_end(20)
        box.add(widget)
        return box

    @staticmethod
    def _lbl(text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text)
        lbl.set_halign(Gtk.Align.START)
        return lbl

    # ── Apply ─────────────────────────────────────────────────────────

    def _on_response(self, _dialog, response: int) -> None:
        if response != Gtk.ResponseType.APPLY:
            return

        # Window
        settings.bottom_offset      = int(self._spin_offset.get_value())
        settings.window_width       = int(self._spin_width.get_value())
        settings.window_height      = int(self._spin_height.get_value())
        settings.list_width         = int(self._spin_list_width.get_value())
        settings.hide_on_focus_loss = self._switch_focus.get_active()
        settings.dock_label         = self._entry_label.get_text().strip() or "Menu"

        # Appearance
        rgba                        = self._color_btn.get_rgba()
        r, g, b                     = int(rgba.red*255), int(rgba.green*255), int(rgba.blue*255)
        settings.background_color   = f"#{r:02x}{g:02x}{b:02x}"
        settings.background_opacity = round(self._scale_opacity.get_value(), 2)

        # Sizes
        settings.tile_icon_size            = int(self._spin_tile_icon.get_value())
        settings.tile_font_size            = int(self._spin_tile_font.get_value())
        settings.list_icon_size            = int(self._spin_list_icon.get_value())
        settings.list_font_size            = int(self._spin_list_font.get_value())
        settings.section_label_font_size   = int(self._spin_section_font.get_value())

        # Animation
        settings.anim_enabled       = self._switch_anim.get_active()
        settings.anim_open_ms       = int(self._spin_open_ms.get_value())
        settings.anim_close_ms      = int(self._spin_close_ms.get_value())
        settings.anim_slide_px      = int(self._spin_slide.get_value())

        settings.save()
        settings.apply_dock_label()
