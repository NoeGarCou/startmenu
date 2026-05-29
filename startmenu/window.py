import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk, GLib

# Frame rate is fixed; duration and slide are user-configurable via settings.
_TICK_MS = 16   # ~60 fps


def _ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)


def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def _ease_in_cubic(t: float) -> float:
    return t * t * t

try:
    import cairo
    _HAS_CAIRO = True
except ImportError:
    _HAS_CAIRO = False

from .settings import settings
from .layout import StartLayout
from .style import apply_css


class StartWindow(Gtk.ApplicationWindow):
    """
    The main launcher window.

    Responsibilities: layout assembly, screen positioning, show/hide/toggle,
    keyboard and focus-loss events, and opening the preferences dialog.
    """

    def __init__(self, application):
        super().__init__(application=application)

        apply_css()
        self.get_style_context().add_class("start-window")

        self._focus_out_armed = True
        self._anim_id    = None
        self._anim_frame = 0
        self._closing    = False

        self._configure_window()
        self._setup_rgba_visual()
        self._build_layout()
        self._connect_signals()

        # Realise all children invisibly, then animate in after a short delay
        # so the window manager has finished mapping the window.
        self.show_all()
        self.set_opacity(0.0)
        self._position()
        GLib.timeout_add(30,  self._start_open_anim)
        GLib.timeout_add(330, self._arm_focus_out)

    # ── Public interface ──────────────────────────────────────────────

    def refresh_pins(self) -> None:
        self._layout._on_pin_changed()

    def toggle(self) -> None:
        if self._closing:
            # Reverse mid-close into an open
            self._do_open()
        elif self.is_visible():
            self._start_close_anim()
        else:
            self._do_open()

    # ── Animation ─────────────────────────────────────────────────────

    def _cancel_anim(self) -> None:
        if self._anim_id is not None:
            GLib.source_remove(self._anim_id)
            self._anim_id = None

    def _final_pos(self) -> tuple:
        screen  = Gdk.Screen.get_default()
        mon     = screen.get_primary_monitor()
        geo     = screen.get_monitor_geometry(mon)
        x = geo.x + (geo.width  - settings.window_width)  // 2
        y = geo.y +  geo.height  - settings.window_height  - settings.bottom_offset
        return x, y

    def _do_open(self) -> None:
        self._layout.reset()
        self._focus_out_armed = False
        self._start_open_anim()
        self._layout.focus_search()
        GLib.timeout_add(300, self._arm_focus_out)

    def _start_open_anim(self) -> bool:
        self._cancel_anim()
        self._closing     = False
        self._anim_frame  = 0
        self._open_frames = max(1, settings.anim_open_ms // _TICK_MS)
        self._slide_px    = settings.anim_slide_px
        x, y = self._final_pos()
        self._anim_x, self._anim_y = x, y
        # Set opacity and position BEFORE show()/present() so the window never
        # appears at its resting position before sliding — that's what caused
        # the visible "jump down then up" on each open.
        if settings.anim_enabled:
            self.set_opacity(0.0)
            self.move(x, y + self._slide_px)
        else:
            self.set_opacity(1.0)
            self.move(x, y)
        if not self.is_visible():
            self.show()
            self.present()
        if settings.anim_enabled:
            self._anim_id = GLib.timeout_add(_TICK_MS, self._tick_open)
        return False  # usable as a one-shot GLib callback

    def _tick_open(self) -> bool:
        self._anim_frame += 1
        t = min(self._anim_frame / self._open_frames, 1.0)
        x, y = self._anim_x, self._anim_y
        self.set_opacity(_ease_out_cubic(t))
        self.move(x, y + int(self._slide_px * (1.0 - _ease_out_expo(t))))
        if t >= 1.0:
            self._anim_id = None
            self.set_opacity(1.0)
            self.move(x, y)
            return False
        return True

    def _start_close_anim(self) -> None:
        if self._closing:
            return
        self._cancel_anim()
        self._closing      = True
        self._anim_frame   = 0
        self._close_frames = max(1, settings.anim_close_ms // _TICK_MS)
        self._slide_px     = settings.anim_slide_px
        x, y = self._final_pos()
        self._anim_x, self._anim_y = x, y
        if not settings.anim_enabled:
            self._closing = False
            self.hide()
            return
        self._anim_id = GLib.timeout_add(_TICK_MS, self._tick_close)

    def _tick_close(self) -> bool:
        self._anim_frame += 1
        t = min(self._anim_frame / self._close_frames, 1.0)
        x, y = self._anim_x, self._anim_y
        self.set_opacity(1.0 - _ease_in_cubic(t))
        self.move(x, y + int(self._slide_px * 0.5 * _ease_in_cubic(t)))
        if t >= 1.0:
            self._anim_id = None
            self._closing = False
            self.hide()
            # Leave opacity at ~0 — _start_open_anim sets it before the next show(),
            # so resetting to 1.0 here would cause a 1-frame flash on reopen.
            return False
        return True

    # ── Setup ─────────────────────────────────────────────────────────

    def _configure_window(self) -> None:
        # UTILITY hint: floating window, no taskbar entry — X11-specific
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_size_request(settings.window_width, settings.window_height)

    def _setup_rgba_visual(self) -> None:
        screen = self.get_screen()
        visual = screen.get_rgba_visual()
        if visual:
            self.set_visual(visual)
        self.set_app_paintable(True)

    def _build_layout(self) -> None:
        self._layout = StartLayout(
            on_launch=self._on_app_launched,
            on_prefs=self._open_preferences,
        )
        self.add(self._layout)

    def _connect_signals(self) -> None:
        self.connect("key-press-event", self._on_key_press)
        if _HAS_CAIRO:
            self.connect("draw", self._on_draw)
        self.connect("focus-out-event", self._on_focus_out)

    # ── Positioning ───────────────────────────────────────────────────

    def _position(self) -> None:
        x, y = self._final_pos()
        self.move(x, y)

    # ── Preferences ───────────────────────────────────────────────────

    def _open_preferences(self) -> None:
        from .preferences import PreferencesDialog
        dlg = PreferencesDialog(parent=self)
        response = dlg.run()
        dlg.destroy()
        if response == Gtk.ResponseType.APPLY:
            self._apply_settings()

    def _apply_settings(self) -> None:
        self.set_size_request(settings.window_width, settings.window_height)
        self._layout.apply_settings()
        self._position()

    # ── Signal handlers ───────────────────────────────────────────────

    def _on_draw(self, _widget, cr) -> bool:
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.0)
        cr.set_operator(cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        return False

    def _on_key_press(self, _widget, event) -> bool:
        if event.keyval == Gdk.KEY_Escape:
            self._start_close_anim()
            return True
        return False

    def _arm_focus_out(self) -> bool:
        self._focus_out_armed = True
        return False

    def _on_focus_out(self, _widget, _event) -> bool:
        if settings.hide_on_focus_loss and self._focus_out_armed:
            # Delay the hide check: a context menu or dialog may grab input
            # immediately after the focus-out (right-click menu, section dialogs).
            # If a GTK grab is active when the timer fires, we stay open.
            GLib.timeout_add(100, self._maybe_hide)
        return False

    def _maybe_hide(self) -> bool:
        if settings.hide_on_focus_loss and self._focus_out_armed:
            if Gtk.grab_get_current() is None and not self.is_active():
                self._start_close_anim()
        return False  # don't repeat

    def _on_app_launched(self) -> None:
        self._start_close_anim()
