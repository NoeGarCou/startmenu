import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Gdk, Pango

from .pinned import pinned_data
from .settings import settings
from .utils import ask_name


class AppList(Gtk.Box):
    """
    Middle panel: search entry + scrollable alphabetical app list.

    - Apps are grouped by first letter with non-interactive letter headers.
    - Typing in the search entry filters both app rows and their letter headers.
    - Right-clicking an app row opens a context menu to pin it to a section.
    - ListBoxRow is a windowless widget; hover is tracked at the ListBox level
      via motion-notify-event + get_row_at_y(), same technique as the FlowBox grid.
    """

    def __init__(self, apps: list, *, on_launch, on_pin_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("app-list-panel")

        self._on_launch = on_launch
        self._on_pin_changed = on_pin_changed
        self._query = ""
        self._hovered_row = None

        # Pre-group by first letter so the filter function can check whole groups
        self._letter_groups: dict[str, list] = {}
        for app in apps:
            letter = self._first_letter(app)
            self._letter_groups.setdefault(letter, []).append(app)

        self._build_search()
        self._build_list()

    # ── Public interface ──────────────────────────────────────────────

    def focus_search(self) -> None:
        self._search.grab_focus()

    def reset(self) -> None:
        self._search.set_text("")

    def rebuild(self) -> None:
        """Recreate all list rows so icon/font size changes take effect."""
        for row in self._listbox.get_children():
            self._listbox.remove(row)
        self._hovered_row = None
        for letter in sorted(self._letter_groups):
            self._add_letter_row(letter)
            for app in self._letter_groups[letter]:
                self._add_app_row(app)
        self._listbox.show_all()

    def reload(self, apps: list) -> None:
        """Replace the full app list (called when new apps are installed/removed)."""
        self._letter_groups = {}
        for app in apps:
            letter = self._first_letter(app)
            self._letter_groups.setdefault(letter, []).append(app)
        self._query = ""
        self._search.set_text("")
        self._hovered_row = None
        self.rebuild()

    # ── Construction ─────────────────────────────────────────────────

    @staticmethod
    def _first_letter(app) -> str:
        name = app.get_display_name()
        ch = name[0].upper() if name else "#"
        return ch if ch.isalpha() else "#"

    def _build_search(self) -> None:
        self._search = Gtk.SearchEntry()
        self._search.set_name("search-entry")
        self._search.set_placeholder_text("Search apps…")
        self._search.connect("changed", self._on_search_changed)
        self._search.set_margin_top(10)
        self._search.set_margin_start(12)
        self._search.set_margin_end(12)
        self.pack_start(self._search, False, False, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.get_style_context().add_class("list-sep")
        sep.set_margin_top(6)
        sep.set_margin_bottom(4)
        self.pack_start(sep, False, False, 0)

    def _build_list(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(10)
        scrolled.set_margin_end(10)
        scrolled.set_margin_bottom(10)

        self._listbox = Gtk.ListBox()
        self._listbox.set_name("app-list-box")
        self._listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._listbox.set_filter_func(self._filter_func)
        self._listbox.connect("row-activated", self._on_row_activated)

        # Hover + right-click at ListBox level (rows are windowless)
        self._listbox.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self._listbox.connect("realize",             self._on_realize)
        self._listbox.connect("motion-notify-event", self._on_motion)
        self._listbox.connect("leave-notify-event",  self._on_leave)
        self._listbox.connect("button-press-event",  self._on_button_press)

        for letter in sorted(self._letter_groups.keys()):
            self._add_letter_row(letter)
            for app in self._letter_groups[letter]:
                self._add_app_row(app)

        scrolled.add(self._listbox)
        self.pack_start(scrolled, True, True, 0)

    def _add_letter_row(self, letter: str) -> None:
        row = Gtk.ListBoxRow()
        row.set_activatable(False)
        row.set_selectable(False)
        row.row_type = "letter"
        row.letter = letter
        row.get_style_context().add_class("letter-row")

        lbl = Gtk.Label(label=letter)
        lbl.get_style_context().add_class("letter-label")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_margin_start(4)
        lbl.set_margin_top(8)
        lbl.set_margin_bottom(2)
        row.add(lbl)
        self._listbox.add(row)

    def _add_app_row(self, app_info) -> None:
        row = Gtk.ListBoxRow()
        row.row_type = "app"
        row.app_info = app_info
        row.letter = self._first_letter(app_info)
        row.get_style_context().add_class("app-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_start(4)
        box.set_margin_end(6)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        icon = app_info.get_icon()
        img = (Gtk.Image.new_from_gicon(icon, Gtk.IconSize.SMALL_TOOLBAR)
               if icon else
               Gtk.Image.new_from_icon_name("application-x-executable", Gtk.IconSize.SMALL_TOOLBAR))
        img.set_pixel_size(settings.list_icon_size)

        lbl = Gtk.Label(label=app_info.get_display_name())
        lbl.get_style_context().add_class("list-app-name")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_hexpand(False)
        lbl.set_max_width_chars(28)
        lbl.set_ellipsize(Pango.EllipsizeMode.END)

        box.pack_start(img, False, False, 0)
        box.pack_start(lbl, False, False, 0)
        row.add(box)
        self._listbox.add(row)

    # ── Hover tracking ────────────────────────────────────────────────

    def _on_realize(self, widget) -> None:
        widget.get_window().set_cursor(
            Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.HAND2)
        )

    def _on_motion(self, listbox, event) -> bool:
        row = listbox.get_row_at_y(int(event.y))
        if row and getattr(row, "row_type", None) != "app":
            row = None  # don't highlight letter headers
        if row is self._hovered_row:
            return False
        if self._hovered_row:
            self._hovered_row.get_style_context().remove_class("hovered")
            self._hovered_row.queue_draw()
        self._hovered_row = row
        if row:
            row.get_style_context().add_class("hovered")
            row.queue_draw()
        return False

    def _on_leave(self, _lb, _ev) -> bool:
        if self._hovered_row:
            self._hovered_row.get_style_context().remove_class("hovered")
            self._hovered_row.queue_draw()
            self._hovered_row = None
        return False

    # ── Right-click context menu ──────────────────────────────────────

    def _on_button_press(self, listbox, event) -> bool:
        if event.button != 3:
            return False
        row = listbox.get_row_at_y(int(event.y))
        if not row or getattr(row, "row_type", None) != "app":
            return False
        self._show_context_menu(row.app_info, event)
        return True

    def _show_context_menu(self, app_info, event) -> None:
        app_id = app_info.get_id()
        menu = Gtk.Menu()

        if pinned_data.sections:
            pin_item = Gtk.MenuItem(label="Pin to menu")
            sub = Gtk.Menu()
            for sec in pinned_data.sections:
                item = Gtk.MenuItem(label=sec.name)
                if app_id and app_id in sec.apps:
                    item.set_sensitive(False)  # already pinned here
                item.connect("activate", lambda _, sid=sec.id: self._do_pin(app_id, sid))
                sub.append(item)
            sub.append(Gtk.SeparatorMenuItem())
            new_item = Gtk.MenuItem(label="New section…")
            new_item.connect("activate", lambda _: self._pin_to_new_section(app_id))
            sub.append(new_item)
            pin_item.set_submenu(sub)
        else:
            pin_item = Gtk.MenuItem(label="Pin to menu…")
            pin_item.connect("activate", lambda _: self._pin_to_new_section(app_id))

        menu.append(pin_item)
        menu.show_all()
        menu.popup_at_pointer(event)

    def _do_pin(self, app_id: str, section_id: str) -> None:
        if app_id:
            pinned_data.pin(app_id, section_id)
            self._on_pin_changed()

    def _pin_to_new_section(self, app_id: str) -> None:
        name = ask_name(self.get_toplevel(), "New Section", "Section name:")
        if name:
            sec = pinned_data.add_section(name)
            if app_id:
                pinned_data.pin(app_id, sec.id)
            self._on_pin_changed()

    # ── Filter ────────────────────────────────────────────────────────

    def _on_search_changed(self, entry) -> None:
        self._query = entry.get_text()
        self._listbox.invalidate_filter()

    def _filter_func(self, row) -> bool:
        if not self._query:
            return True
        q = self._query.casefold()
        if row.row_type == "letter":
            # Show letter header only if at least one app in its group matches
            return any(
                q in a.get_display_name().casefold()
                for a in self._letter_groups.get(row.letter, [])
            )
        return q in row.app_info.get_display_name().casefold()

    # ── Launch ────────────────────────────────────────────────────────

    def _on_row_activated(self, _lb, row) -> None:
        if row.row_type != "app":
            return
        try:
            row.app_info.launch([], None)
        except Exception as exc:
            print(f"StartMenu: {exc}", file=sys.stderr)
        self._on_launch()
