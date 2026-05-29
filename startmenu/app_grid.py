import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

from .app_item import AppItem
from .app_source import matches_query


class AppGrid(Gtk.Box):
    """
    Composite widget: search row (entry + gear button) on top,
    scrollable FlowBox grid below.

    on_launch -- zero-argument callable; called after a successful launch so the
                 window can hide itself.
    on_prefs  -- zero-argument callable; called when the gear button is clicked.
    """

    def __init__(self, apps: list, *, on_launch, on_prefs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._all_apps = apps
        self._query = ""
        self._on_launch = on_launch
        self._on_prefs = on_prefs
        self._hovered_child = None

        self._build_search_row()
        self._build_grid()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def focus_search(self) -> None:
        self._search.grab_focus()

    def reset(self) -> None:
        self._search.set_text("")

    # ------------------------------------------------------------------
    # Widget construction
    # ------------------------------------------------------------------

    def _build_search_row(self) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_name("search-row")

        self._search = Gtk.SearchEntry()
        self._search.set_name("search-entry")
        self._search.set_placeholder_text("Search apps…")
        self._search.connect("changed", self._on_search_changed)
        row.pack_start(self._search, True, True, 0)

        gear = Gtk.Button()
        gear.set_name("gear-button")
        gear.set_relief(Gtk.ReliefStyle.NONE)
        gear.set_focus_on_click(False)
        gear.add(Gtk.Image.new_from_icon_name("preferences-system-symbolic", Gtk.IconSize.BUTTON))
        gear.set_tooltip_text("StartMenu preferences")
        gear.connect("clicked", lambda _btn: self._on_prefs())
        row.pack_start(gear, False, False, 0)

        self.pack_start(row, False, False, 0)

    def _build_grid(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_valign(Gtk.Align.START)
        self._flowbox.set_homogeneous(True)
        self._flowbox.set_max_children_per_line(6)
        self._flowbox.set_min_children_per_line(3)
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_column_spacing(0)
        self._flowbox.set_row_spacing(0)
        self._flowbox.set_filter_func(self._filter_func)
        self._flowbox.connect("child-activated", self._on_child_activated)

        # FlowBox has its own GdkWindow so motion events work reliably here.
        # FlowBoxChild is windowless — pointer events must be tracked from the parent.
        self._flowbox.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self._flowbox.connect("realize",              self._on_grid_realize)
        self._flowbox.connect("motion-notify-event",  self._on_motion)
        self._flowbox.connect("leave-notify-event",   self._on_grid_leave)
        self._flowbox.connect("button-press-event",   self._on_grid_press)
        self._flowbox.connect("button-release-event", self._on_grid_release)

        for app in self._all_apps:
            self._flowbox.add(AppItem(app))

        scrolled.add(self._flowbox)
        self.pack_start(scrolled, True, True, 0)

    # ------------------------------------------------------------------
    # Grid-level pointer event handlers
    # ------------------------------------------------------------------

    def _on_grid_realize(self, widget) -> None:
        widget.get_window().set_cursor(
            Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.HAND2)
        )

    def _on_motion(self, flowbox, event) -> bool:
        child = flowbox.get_child_at_pos(int(event.x), int(event.y))
        if child is self._hovered_child:
            return False
        if self._hovered_child:
            self._hovered_child.get_style_context().remove_class("hovered")
            self._hovered_child.queue_draw()
        self._hovered_child = child
        if child:
            child.get_style_context().add_class("hovered")
            child.queue_draw()
        return False

    def _on_grid_leave(self, _flowbox, _event) -> bool:
        if self._hovered_child:
            ctx = self._hovered_child.get_style_context()
            ctx.remove_class("hovered")
            ctx.remove_class("pressed")
            self._hovered_child.queue_draw()
            self._hovered_child = None
        return False

    def _on_grid_press(self, _flowbox, _event) -> bool:
        if self._hovered_child:
            self._hovered_child.get_style_context().add_class("pressed")
            self._hovered_child.queue_draw()
        return False

    def _on_grid_release(self, _flowbox, _event) -> bool:
        if self._hovered_child:
            self._hovered_child.get_style_context().remove_class("pressed")
            self._hovered_child.queue_draw()
        return False

    # ------------------------------------------------------------------
    # Search / filter handlers
    # ------------------------------------------------------------------

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._query = entry.get_text()
        self._flowbox.invalidate_filter()

    def _filter_func(self, child: AppItem) -> bool:
        if not self._query:
            return True
        return matches_query(child.app_info, self._query)

    def _on_child_activated(self, _flowbox: Gtk.FlowBox, child: AppItem) -> None:
        try:
            child.app_info.launch([], None)
        except Exception as exc:
            print(
                f"StartMenu: failed to launch {child.app_info.get_display_name()!r}: {exc}",
                file=sys.stderr,
            )
        self._on_launch()
