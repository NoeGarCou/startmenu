import sys

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("Gio", "2.0")
from gi.repository import Gtk, Gdk, Gio

from .app_item import AppItem
from .folder_info import (FolderInfo, is_folder_id, path_from_id,
                          FileInfo, is_file_id, file_path_from_id, make_file_id)
from .pinned import pinned_data
from .utils import ask_name

# Two separate MIME types so GTK routes each drag to the correct target.
# A single type caused section drags to land on FlowBoxes (which rejected them)
# and tile drags to land on section wrappers (which also rejected them).
_TILE_TARGET    = Gtk.TargetEntry.new("application/x-startmenu-tile",    Gtk.TargetFlags.SAME_APP, 1)
_SECTION_TARGET = Gtk.TargetEntry.new("application/x-startmenu-section", Gtk.TargetFlags.SAME_APP, 2)

_SEP = "\x1e"   # ASCII record separator


class SectionWidget(Gtk.Box):
    """
    One section: drag-handle + name label + ⋮ menu, then a tile FlowBox.

    Drag routing:
      - Header EventBox  → source for _SECTION_TARGET (section reorder)
      - FlowBox          → source for _TILE_TARGET     (tile move / sort)
      - FlowBox          → dest   for _TILE_TARGET     (receives tile drops)
    """

    def __init__(self, section, app_map: dict, *, on_launch, on_pin_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._section        = section
        self._app_map        = app_map
        self._on_launch      = on_launch
        self._on_pin_changed = on_pin_changed
        self._hovered_child      = None
        self._drag_child         = None   # AppItem being dragged out of this section
        self._drag_press_x       = 0
        self._drag_press_y       = 0
        self._drop_indicator     = None   # AppItem currently showing the drop-before CSS class
        self._insert_before_id   = None   # app_id to insert before on drop (cached at motion time)

        self._build_header()
        self._build_tiles()

    # ── Header ────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        header.get_style_context().add_class("section-header")

        # EventBox needed: Gtk.Box is windowless and can't be a DnD source.
        handle = Gtk.EventBox()
        handle.get_style_context().add_class("drag-handle")
        handle.set_tooltip_text("Drag to reorder sections")
        handle.set_margin_end(6)
        handle.add(Gtk.Label(label="⠿"))
        handle.drag_source_set(
            Gdk.ModifierType.BUTTON1_MASK, [_SECTION_TARGET], Gdk.DragAction.MOVE
        )
        handle.connect("drag-begin",    self._on_section_drag_begin)
        handle.connect("drag-data-get", self._on_section_drag_data_get)
        handle.connect("realize", lambda w: w.get_window().set_cursor(
            Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.FLEUR)
        ))
        header.pack_start(handle, False, False, 0)

        self._name_label = Gtk.Label(label=self._section.name.upper())
        self._name_label.get_style_context().add_class("section-name-label")
        self._name_label.set_halign(Gtk.Align.START)
        self._name_label.set_hexpand(True)
        header.pack_start(self._name_label, True, True, 0)

        menu_btn = Gtk.Button()
        menu_btn.set_name("section-menu-btn")
        menu_btn.set_relief(Gtk.ReliefStyle.NONE)
        menu_btn.set_focus_on_click(False)
        menu_btn.set_tooltip_text("Section options")
        menu_btn.add(Gtk.Image.new_from_icon_name(
            "view-more-symbolic", Gtk.IconSize.SMALL_TOOLBAR
        ))
        menu_btn.connect("clicked", self._on_section_menu_clicked)
        header.pack_start(menu_btn, False, False, 0)

        self.pack_start(header, False, False, 0)

    # ── Tiles ─────────────────────────────────────────────────────────

    def _build_tiles(self) -> None:
        self._flowbox = Gtk.FlowBox()
        self._flowbox.set_homogeneous(True)
        self._flowbox.set_max_children_per_line(7)
        self._flowbox.set_min_children_per_line(1)
        self._flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flowbox.set_column_spacing(0)
        self._flowbox.set_row_spacing(0)
        self._flowbox.set_valign(Gtk.Align.START)
        # Minimum height so an empty section still has a valid drop area.
        self._flowbox.set_size_request(-1, 80)
        self._flowbox.connect("child-activated", self._on_tile_activated)

        # Hover / right-click / drag detection (FlowBoxChild is windowless).
        # drag_source_set conflicts with FlowBox's own button handling, so we
        # detect the drag threshold manually in _on_motion and call
        # drag_begin_with_coordinates ourselves.
        self._flowbox.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK |
            Gdk.EventMask.BUTTON_PRESS_MASK   |
            Gdk.EventMask.BUTTON_RELEASE_MASK |
            Gdk.EventMask.BUTTON_MOTION_MASK
        )
        self._flowbox.connect("realize",              self._on_grid_realize)
        self._flowbox.connect("motion-notify-event",  self._on_motion)
        self._flowbox.connect("leave-notify-event",   self._on_grid_leave)
        self._flowbox.connect("button-press-event",   self._on_grid_press)
        self._flowbox.connect("button-release-event", self._on_grid_release)

        # Tile drag source callbacks — drag is started manually in _on_motion.
        self._flowbox.connect("drag-begin",    self._on_tile_drag_begin)
        self._flowbox.connect("drag-data-get", self._on_tile_drag_data_get)
        self._flowbox.connect("drag-end",      self._on_tile_drag_end)

        # Tile drag DESTINATION — only accepts _TILE_TARGET, never _SECTION_TARGET.
        # DestDefaults.MOTION is intentionally excluded: it installs its own
        # drag-motion handler that returns True and stops signal emission via the
        # boolean accumulator, preventing our custom handler from ever running.
        # We call Gdk.drag_status() ourselves inside _on_tile_drag_motion.
        self._flowbox.drag_dest_set(
            Gtk.DestDefaults.DROP,
            [_TILE_TARGET],
            Gdk.DragAction.MOVE,
        )
        self._flowbox.connect("drag-motion",        self._on_tile_drag_motion)
        self._flowbox.connect("drag-leave",         self._on_tile_drag_leave)
        self._flowbox.connect("drag-data-received", self._on_tile_drop_received)

        self._populate_tiles()
        self.pack_start(self._flowbox, False, False, 0)

    def _populate_tiles(self) -> None:
        for child in self._flowbox.get_children():
            self._flowbox.remove(child)
        for app_id in self._section.apps:
            if is_folder_id(app_id):
                label     = pinned_data.folder_labels.get(app_id)
                icon_name = pinned_data.folder_icons.get(app_id)
                app_info  = FolderInfo(path_from_id(app_id), label=label, icon_name=icon_name)
            elif is_file_id(app_id):
                label     = pinned_data.folder_labels.get(app_id)
                icon_name = pinned_data.folder_icons.get(app_id)
                app_info  = FileInfo(file_path_from_id(app_id), label=label, icon_name=icon_name)
            else:
                app_info = self._app_map.get(app_id)
            if app_info:
                self._flowbox.add(AppItem(app_info))
        self._flowbox.show_all()

    def refresh(self) -> None:
        updated = pinned_data.get_section(self._section.id)
        if updated:
            self._section    = updated
            self._name_label.set_text(self._section.name.upper())
            self._hovered_child = None
            self._drag_child    = None
            self._clear_drop_indicator()
            self._populate_tiles()

    # ── Section drag (header handle is source) ────────────────────────

    def _on_section_drag_begin(self, _handle, context) -> None:
        Gtk.drag_set_icon_name(context, "view-list-symbolic", 0, 0)

    def _on_section_drag_data_get(self, _handle, _ctx, sel, _info, _time) -> None:
        # set_text() only works for standard text atoms; use set() for custom MIME types.
        sel.set(sel.get_target(), 8, self._section.id.encode())

    # ── Tile drag ─────────────────────────────────────────────────────

    def _on_tile_drag_begin(self, _fb, context) -> None:
        if not self._drag_child:
            return
        self._drag_child.get_style_context().add_class("dragging")
        self._drag_child.queue_draw()
        icon = self._drag_child.app_info.get_icon()
        if icon:
            try:
                info = Gtk.IconTheme.get_default().lookup_by_gicon(
                    icon, 48, Gtk.IconLookupFlags(0)
                )
                if info:
                    Gtk.drag_set_icon_pixbuf(context, info.load_icon(), 24, 24)
                    return
            except Exception:
                pass
        Gtk.drag_set_icon_default(context)

    def _on_tile_drag_data_get(self, _fb, _ctx, sel, _info, _time) -> None:
        if self._drag_child:
            app_id = self._drag_child.app_info.get_id() or ""
            payload = f"{app_id}{_SEP}{self._section.id}".encode()
            sel.set(sel.get_target(), 8, payload)

    def _on_tile_drag_end(self, _fb, _ctx) -> None:
        if self._drag_child:
            ctx = self._drag_child.get_style_context()
            ctx.remove_class("pressed")
            ctx.remove_class("hovered")
            ctx.remove_class("dragging")
            self._drag_child.queue_draw()
            self._drag_child = None
        self._clear_drop_indicator()

    # ── Drop indicator (CSS left-border, no structural FlowBox changes) ──

    def _clear_drop_indicator(self) -> None:
        if self._drop_indicator:
            self._drop_indicator.get_style_context().remove_class("drop-before")
            self._drop_indicator.queue_draw()
            self._drop_indicator = None

    # ── Tile drop destination ─────────────────────────────────────────

    def _on_tile_drag_motion(self, flowbox, context, x, y, time) -> bool:
        flowbox.get_style_context().add_class("tile-drop-target")

        raw   = flowbox.get_child_at_pos(int(x), int(y))
        # Dragged tile is not a valid drop target; empty space means "append".
        target = raw if (raw is not None and raw is not self._drag_child) else None

        if target is not self._drop_indicator:
            self._clear_drop_indicator()
            self._drop_indicator    = target
            self._insert_before_id  = target.app_info.get_id() if target else None
            if target:
                target.get_style_context().add_class("drop-before")
                target.queue_draw()

        Gdk.drag_status(context, Gdk.DragAction.MOVE, time)
        return True

    def _on_tile_drag_leave(self, flowbox, _ctx, _time) -> None:
        flowbox.get_style_context().remove_class("tile-drop-target")
        self._clear_drop_indicator()
        # _insert_before_id is intentionally NOT cleared here.
        # drag-leave fires before drag-data-received in GTK3; the drop handler
        # still needs the cached value to know where to insert.

    def _on_tile_drop_received(self, flowbox, context, x, y, data, _info, time) -> None:
        raw  = data.get_data()
        text = bytes(raw).decode() if raw else ""
        if _SEP not in text:
            Gtk.drag_finish(context, False, False, time)
            return

        app_id, from_section_id = text.split(_SEP, 1)
        if not app_id:
            Gtk.drag_finish(context, False, False, time)
            return

        before_id              = self._insert_before_id
        self._insert_before_id = None

        if from_section_id == self._section.id:
            # ── Intra-section sort ────────────────────────────────────
            apps = self._section.apps
            if app_id in apps:
                apps.remove(app_id)
                if before_id and before_id in apps:
                    apps.insert(apps.index(before_id), app_id)
                else:
                    apps.append(app_id)
            pinned_data.save()
        else:
            # ── Inter-section move ────────────────────────────────────
            src = pinned_data.get_section(from_section_id)
            if src and app_id in src.apps:
                src.apps.remove(app_id)
            if app_id not in self._section.apps:
                if before_id and before_id in self._section.apps:
                    self._section.apps.insert(
                        self._section.apps.index(before_id), app_id
                    )
                else:
                    self._section.apps.append(app_id)
            pinned_data.save()

        Gtk.drag_finish(context, True, True, time)
        self._on_pin_changed()

    # ── Grid hover tracking ───────────────────────────────────────────

    def _on_grid_realize(self, widget) -> None:
        widget.get_window().set_cursor(
            Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.HAND2)
        )

    def _on_motion(self, flowbox, event) -> bool:
        # When button1 is held over a drag candidate, check the GTK drag threshold.
        # Once exceeded, start the drag manually — more reliable than drag_source_set
        # on a FlowBox, which can conflict with FlowBox's own button handling.
        if (event.state & Gdk.ModifierType.BUTTON1_MASK) and self._drag_child:
            threshold = Gtk.Settings.get_default().props.gtk_dnd_drag_threshold
            if (abs(event.x - self._drag_press_x) > threshold or
                    abs(event.y - self._drag_press_y) > threshold):
                targets = Gtk.TargetList.new([_TILE_TARGET])
                flowbox.drag_begin_with_coordinates(
                    targets, Gdk.DragAction.MOVE, 1, event,
                    int(self._drag_press_x), int(self._drag_press_y),
                )
                return True

        # Hover tracking (button not held)
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

    def _on_grid_leave(self, _fb, _ev) -> bool:
        if self._hovered_child:
            ctx = self._hovered_child.get_style_context()
            ctx.remove_class("hovered")
            ctx.remove_class("pressed")
            self._hovered_child.queue_draw()
            self._hovered_child = None
        return False

    def _on_grid_press(self, flowbox, event) -> bool:
        child = flowbox.get_child_at_pos(int(event.x), int(event.y))
        if event.button == 3:
            if child:
                self._show_tile_menu(child.app_info, event)
            return True
        if event.button == 1 and child:
            self._drag_child   = child
            self._drag_press_x = event.x
            self._drag_press_y = event.y
            child.get_style_context().add_class("pressed")
            child.queue_draw()
        else:
            self._drag_child = None
        return False

    def _on_grid_release(self, _fb, _ev) -> bool:
        self._drag_child = None  # cancel any pending drag that never crossed the threshold
        if self._hovered_child:
            self._hovered_child.get_style_context().remove_class("pressed")
            self._hovered_child.queue_draw()
        return False

    # ── Section header menu ───────────────────────────────────────────

    def _on_section_menu_clicked(self, btn) -> None:
        menu = Gtk.Menu()
        pin_folder = Gtk.MenuItem(label="Pin folder…")
        pin_folder.connect("activate", lambda _: self._pin_folder())
        menu.append(pin_folder)
        pin_file = Gtk.MenuItem(label="Pin file…")
        pin_file.connect("activate", lambda _: self._pin_file())
        menu.append(pin_file)
        menu.append(Gtk.SeparatorMenuItem())
        rename = Gtk.MenuItem(label="Rename section…")
        rename.connect("activate", lambda _: self._rename_section())
        menu.append(rename)
        delete = Gtk.MenuItem(label="Delete section")
        delete.connect("activate", lambda _: self._delete_section())
        menu.append(delete)
        menu.show_all()
        menu.popup_at_widget(btn, Gdk.Gravity.SOUTH_EAST, Gdk.Gravity.NORTH_EAST, None)

    def _pin_folder(self) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Choose a folder to pin",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Pin",    Gtk.ResponseType.OK,
        )
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if path:
                from .folder_info import make_id
                pinned_data.pin(make_id(path), self._section.id)
                self._on_pin_changed()
        dialog.destroy()

    def _pin_file(self) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Choose a file to pin",
            parent=self.get_toplevel(),
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons(
            "_Cancel", Gtk.ResponseType.CANCEL,
            "_Pin",    Gtk.ResponseType.OK,
        )
        if dialog.run() == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            if path:
                pinned_data.pin(make_file_id(path), self._section.id)
                self._on_pin_changed()
        dialog.destroy()

    def _rename_section(self) -> None:
        name = ask_name(self.get_toplevel(), "Rename Section",
                        "New name:", self._section.name)
        if name:
            pinned_data.rename_section(self._section.id, name)
            self._on_pin_changed()

    def _delete_section(self) -> None:
        pinned_data.remove_section(self._section.id)
        self._on_pin_changed()

    # ── Tile right-click menu ─────────────────────────────────────────

    def _show_tile_menu(self, app_info, event) -> None:
        app_id = app_info.get_id()
        menu   = Gtk.Menu()

        if is_folder_id(app_id) or is_file_id(app_id):
            rename = Gtk.MenuItem(label="Rename tile…")
            rename.connect("activate", lambda _: self._rename_folder_tile(app_id, app_info))
            menu.append(rename)
            change_icon = Gtk.MenuItem(label="Change icon…")
            change_icon.connect("activate", lambda _: self._change_folder_icon(app_id, app_info))
            menu.append(change_icon)
            menu.append(Gtk.SeparatorMenuItem())

        unpin = Gtk.MenuItem(label="Unpin")
        unpin.connect("activate", lambda _: self._do_unpin(app_id))
        menu.append(unpin)

        other = [s for s in pinned_data.sections if s.id != self._section.id]
        if other:
            move_item = Gtk.MenuItem(label="Move to")
            sub = Gtk.Menu()
            for sec in other:
                item = Gtk.MenuItem(label=sec.name)
                item.connect("activate", lambda _, to=sec.id: self._do_move(app_id, to))
                sub.append(item)
            move_item.set_submenu(sub)
            menu.append(move_item)

        menu.show_all()
        menu.popup_at_pointer(event)

    def _rename_folder_tile(self, app_id: str, app_info) -> None:
        current_override = pinned_data.folder_labels.get(app_id, "")
        auto_name        = app_info.get_display_name()

        parent = self.get_toplevel()
        win    = parent if (parent and parent.is_toplevel()) else None
        dlg    = Gtk.Dialog(title="Rename Tile", parent=win, modal=True,
                            destroy_with_parent=True)
        dlg.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_OK", Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.set_default_size(300, -1)

        area = dlg.get_content_area()
        area.set_spacing(6)
        area.set_margin_top(16)
        area.set_margin_bottom(8)
        area.set_margin_start(20)
        area.set_margin_end(20)

        area.add(Gtk.Label(label="Display name:", halign=Gtk.Align.START))
        entry = Gtk.Entry()
        entry.set_text(current_override)
        entry.set_placeholder_text(auto_name)   # shows auto name as greyed hint
        entry.set_activates_default(True)
        area.add(entry)

        hint = Gtk.Label(halign=Gtk.Align.START)
        hint.set_markup(f"<small>Leave empty to use automatic name: <i>{auto_name}</i></small>")
        area.add(hint)

        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK:
            label = entry.get_text().strip() or None  # None → clear override → use auto
            pinned_data.set_folder_label(app_id, label)
            self._on_pin_changed()
        dlg.destroy()

    def _change_folder_icon(self, app_id: str, app_info) -> None:
        current = pinned_data.folder_icons.get(app_id, "")

        parent = self.get_toplevel()
        win    = parent if (parent and parent.is_toplevel()) else None
        dlg    = Gtk.Dialog(title="Change Icon", parent=win, modal=True,
                            destroy_with_parent=True)
        dlg.add_buttons("_Cancel", Gtk.ResponseType.CANCEL, "_Apply", Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        dlg.set_default_size(380, -1)

        area = dlg.get_content_area()
        area.set_spacing(10)
        area.set_margin_top(16)
        area.set_margin_bottom(8)
        area.set_margin_start(20)
        area.set_margin_end(20)

        # Preview + entry row
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        preview = Gtk.Image()
        preview.set_pixel_size(48)

        def _refresh_preview(name):
            icon = Gio.ThemedIcon.new(name) if name else app_info.get_icon()
            preview.set_from_gicon(icon, Gtk.IconSize.DIALOG)

        entry = Gtk.Entry()
        entry.set_text(current)
        entry.set_placeholder_text("icon-name  (empty = automatic)")
        entry.set_activates_default(True)
        entry.set_hexpand(True)
        entry.connect("changed", lambda e: _refresh_preview(e.get_text().strip()))
        _refresh_preview(current)

        row.pack_start(preview, False, False, 0)
        row.pack_start(entry,   True,  True,  0)
        area.add(row)

        # Clickable suggestions
        area.add(Gtk.Label(label="Common icons:", halign=Gtk.Align.START))
        _SUGGESTIONS = [
            "folder", "folder-documents", "folder-download", "folder-music",
            "folder-pictures", "folder-videos", "folder-publicshare",
            "user-home", "user-desktop", "computer",
            "drive-harddisk", "network-workgroup",
        ]
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(6)
        flow.set_column_spacing(4)
        flow.set_row_spacing(4)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        for name in _SUGGESTIONS:
            btn = Gtk.Button()
            btn.set_tooltip_text(name)
            btn.set_relief(Gtk.ReliefStyle.NONE)
            btn.add(Gtk.Image.new_from_icon_name(name, Gtk.IconSize.LARGE_TOOLBAR))
            btn.connect("clicked", lambda _, n=name: (entry.set_text(n), _refresh_preview(n)))
            flow.add(btn)
        area.add(flow)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hint = Gtk.Label(
            label="Leave empty to restore the automatic icon.",
            halign=Gtk.Align.START,
        )
        hint.set_hexpand(True)
        browse_btn = Gtk.Button(label="Browse all icons…")
        browse_btn.set_relief(Gtk.ReliefStyle.NONE)
        browse_btn.connect("clicked", lambda _: self._browse_icons(
            lambda n: (entry.set_text(n), _refresh_preview(n))
        ))
        bottom.pack_start(hint,       True,  True,  0)
        bottom.pack_start(browse_btn, False, False, 0)
        area.add(bottom)

        dlg.show_all()
        if dlg.run() == Gtk.ResponseType.OK:
            icon_name = entry.get_text().strip() or None
            pinned_data.set_folder_icon(app_id, icon_name)
            self._on_pin_changed()
        dlg.destroy()

    def _browse_icons(self, on_select) -> None:
        """Searchable browser over the full active icon theme. Calls on_select(name) on pick."""
        theme     = Gtk.IconTheme.get_default()
        all_icons = sorted(theme.list_icons(None))

        parent = self.get_toplevel()
        win    = parent if (parent and parent.is_toplevel()) else None
        dlg    = Gtk.Dialog(title="Browse Icons", parent=win, modal=True,
                            destroy_with_parent=True)
        dlg.add_button("_Close", Gtk.ResponseType.CLOSE)
        dlg.set_default_size(540, 500)

        area = dlg.get_content_area()
        area.set_spacing(8)
        area.set_margin_top(12)
        area.set_margin_bottom(8)
        area.set_margin_start(12)
        area.set_margin_end(12)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search icons… (type to filter)")
        area.add(search)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(9)
        flow.set_column_spacing(2)
        flow.set_row_spacing(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        scrolled.add(flow)
        area.add(scrolled)

        count_lbl = Gtk.Label(halign=Gtk.Align.END)
        area.add(count_lbl)

        _MAX = 200

        def _populate(query: str) -> None:
            for ch in flow.get_children():
                flow.remove(ch)
            q       = query.strip().lower()
            matches = [n for n in all_icons if q in n] if q else all_icons
            shown   = matches[:_MAX]
            for name in shown:
                btn = Gtk.Button()
                btn.set_tooltip_text(name)
                btn.set_relief(Gtk.ReliefStyle.NONE)
                img = Gtk.Image.new_from_icon_name(name, Gtk.IconSize.LARGE_TOOLBAR)
                img.set_pixel_size(32)
                btn.add(img)
                def _pick(_, n=name):
                    on_select(n)
                    dlg.response(Gtk.ResponseType.CLOSE)
                btn.connect("clicked", _pick)
                flow.add(btn)
            total = len(matches)
            if total > _MAX:
                count_lbl.set_text(f"Showing {_MAX} of {total} — refine your search")
            else:
                count_lbl.set_text(f"{total} icon{'s' if total != 1 else ''}")
            flow.show_all()

        search.connect("search-changed", lambda e: _populate(e.get_text()))
        _populate("")

        dlg.show_all()
        dlg.run()
        dlg.destroy()

    def _do_unpin(self, app_id: str) -> None:
        pinned_data.unpin(app_id, self._section.id)
        self._on_pin_changed()

    def _do_move(self, app_id: str, to_id: str) -> None:
        pinned_data.move(app_id, self._section.id, to_id)
        self._on_pin_changed()

    # ── Launch ────────────────────────────────────────────────────────

    def _on_tile_activated(self, _fb, child) -> None:
        try:
            child.app_info.launch([], None)
        except Exception as exc:
            print(f"StartMenu: {exc}", file=sys.stderr)
        self._on_launch()


# ─────────────────────────────────────────────────────────────────────────────


class PinnedPanel(Gtk.Box):
    """
    Right panel: scrollable SectionWidgets + "Add section" hint.

    Each SectionWidget is wrapped in a Gtk.EventBox which is the drop target
    for _SECTION_TARGET drags (Gtk.Box is windowless and can't receive drops).
    The EventBox only accepts _SECTION_TARGET, so tile drags pass through to
    the FlowBox inside the SectionWidget.
    """

    def __init__(self, app_map: dict, *, on_launch, on_pin_changed):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_name("pinned-panel")
        self._app_map        = app_map
        self._on_launch      = on_launch
        self._on_pin_changed = on_pin_changed

        self._build()

    # ── Public interface ──────────────────────────────────────────────

    def refresh(self) -> None:
        for child in self._content_box.get_children():
            self._content_box.remove(child)
        self._populate()
        self._content_box.show_all()

    # ── Construction ─────────────────────────────────────────────────

    def _build(self) -> None:
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_margin_start(12)
        scrolled.set_margin_end(12)
        scrolled.set_margin_top(10)
        scrolled.set_margin_bottom(10)

        self._content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self._content_box.set_hexpand(True)
        self._content_box.set_margin_end(10)
        self._populate()

        scrolled.add(self._content_box)
        self.pack_start(scrolled, True, True, 0)

    def _populate(self) -> None:
        if not pinned_data.sections:
            hint = Gtk.Label(label="Right-click any app to pin it here")
            hint.get_style_context().add_class("empty-hint")
            hint.set_halign(Gtk.Align.CENTER)
            hint.set_valign(Gtk.Align.CENTER)
            hint.set_vexpand(True)
            self._content_box.pack_start(hint, True, True, 0)

        for section in pinned_data.sections:
            widget = SectionWidget(
                section, self._app_map,
                on_launch=self._on_launch,
                on_pin_changed=self._on_pin_changed,
            )
            # EventBox wrapper — provides a GdkWindow for section-reorder drops.
            # It only accepts _SECTION_TARGET so tile drags pass through to the
            # FlowBox inside the SectionWidget.
            wrapper = Gtk.EventBox()
            wrapper.section_id = section.id
            wrapper.add(widget)
            wrapper.drag_dest_set(
                Gtk.DestDefaults.DROP,
                [_SECTION_TARGET],
                Gdk.DragAction.MOVE,
            )
            wrapper.connect("drag-motion",        self._on_section_drag_motion)
            wrapper.connect("drag-leave",         self._on_section_drag_leave)
            wrapper.connect("drag-data-received", self._on_section_drop_received)
            self._content_box.pack_start(wrapper, False, False, 0)

        # End-of-list drop zone — lets the user move a section to the last position.
        # Only useful when there are sections to reorder.
        if pinned_data.sections:
            end_zone = Gtk.EventBox()
            end_zone.section_id = None   # None = "append to end"
            end_zone.set_size_request(-1, 24)
            end_zone.drag_dest_set(
                Gtk.DestDefaults.DROP,
                [_SECTION_TARGET],
                Gdk.DragAction.MOVE,
            )
            end_zone.connect("drag-motion",        self._on_section_drag_motion)
            end_zone.connect("drag-leave",         self._on_section_drag_leave)
            end_zone.connect("drag-data-received", self._on_section_drop_received)
            self._content_box.pack_start(end_zone, False, False, 0)

        add_btn = Gtk.Button(label="+ Add section")
        add_btn.get_style_context().add_class("add-section-hint")
        add_btn.set_relief(Gtk.ReliefStyle.NONE)
        add_btn.set_focus_on_click(False)
        add_btn.connect("clicked", self._on_add_section)
        self._content_box.pack_start(add_btn, False, False, 0)

    # ── Section drop (reorder) ────────────────────────────────────────

    def _on_section_drag_motion(self, wrapper, context, x, y, time) -> bool:
        # Only highlight when a section drag (not a tile drag) is over this wrapper.
        section_atom = Gdk.Atom.intern("application/x-startmenu-section", False)
        if section_atom not in context.list_targets():
            Gdk.drag_status(context, 0, time)
            return False
        wrapper.get_style_context().add_class("section-drop-target")
        Gdk.drag_status(context, Gdk.DragAction.MOVE, time)
        return True

    def _on_section_drag_leave(self, wrapper, _ctx, _time) -> None:
        wrapper.get_style_context().remove_class("section-drop-target")

    def _on_section_drop_received(self, wrapper, context, x, y, data, _info, time) -> None:
        raw = data.get_data()
        from_id = bytes(raw).decode() if raw else ""
        to_id   = wrapper.section_id   # None = end-zone (append to end)

        if not from_id or from_id == to_id:
            Gtk.drag_finish(context, False, False, time)
            return

        sections = pinned_data.sections
        from_idx = next((i for i, s in enumerate(sections) if s.id == from_id), None)
        if from_idx is None:
            Gtk.drag_finish(context, False, False, time)
            return

        section = sections.pop(from_idx)
        if to_id is None:
            sections.append(section)
        else:
            # Look up to_idx after the pop so indices are already adjusted.
            to_idx = next((i for i, s in enumerate(sections) if s.id == to_id), None)
            sections.insert(to_idx if to_idx is not None else len(sections), section)

        pinned_data.save()
        Gtk.drag_finish(context, True, True, time)
        self._on_pin_changed()

    def _on_add_section(self, _btn) -> None:
        name = ask_name(self.get_toplevel(), "New Section", "Section name:")
        if name:
            pinned_data.add_section(name)
            self._on_pin_changed()
