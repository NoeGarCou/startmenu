import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, Gdk

CSS = """

/* ── Window ──────────────────────────────────────────────────────────────── */

window.start-window {
    background-color: transparent;
}

#start-container {
    background-color: rgba(28, 28, 40, 0.97);
    border-radius: 18px;
}

/* ── Power strip (left column) ───────────────────────────────────────────── */

#power-strip {
    padding: 10px 6px;
    min-width: 50px;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

#strip-btn {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    padding: 7px;
    min-width: 34px;
    min-height: 34px;
    color: rgba(255, 255, 255, 0.40);
    transition: background-color 120ms ease, color 120ms ease;
}

#strip-btn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    color: rgba(255, 255, 255, 0.90);
}

#strip-btn:active {
    background-color: rgba(255, 255, 255, 0.20);
}

/* ── App list panel (middle column) ──────────────────────────────────────── */

/* Padding is handled in Python via set_margin_* on content widgets
   so GTK theme defaults cannot interfere. */
#app-list-panel {
    padding: 0;
    border-right: 1px solid rgba(255, 255, 255, 0.06);
}

#search-entry {
    background-color: rgba(255, 255, 255, 0.07);
    color: rgba(255, 255, 255, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 8px 12px;
    font-size: 13px;
    caret-color: rgba(255, 255, 255, 0.7);
    margin-bottom: 2px;
}

#search-entry:focus {
    border-color: rgba(255, 255, 255, 0.28);
    box-shadow: none;
}

.list-sep {
    background-color: rgba(255, 255, 255, 0.06);
    margin-left: 4px;
    margin-right: 4px;
}

#app-list-box {
    background-color: transparent;
}

/* Explicitly zero GTK's default ListBoxRow padding/margin so our
   Python-level content margins are the only offset. */
#app-list-box row {
    padding: 3px 6px;
    margin: 0;
    background-color: transparent;
    border-radius: 8px;
    transition: background-color 120ms ease;
}

.letter-row {
    /* non-interactive — no hover */
}

.app-row.hovered {
    background-color: rgba(255, 255, 255, 0.10);
    transition: background-color 80ms ease;
}

.app-row.hovered .list-app-name {
    color: rgba(255, 255, 255, 1.0);
}

.letter-label {
    color: rgba(255, 255, 255, 0.30);
    font-size: 10px;
    font-weight: bold;
}

.list-app-name {
    color: rgba(255, 255, 255, 0.82);
    font-size: 13px;
    transition: color 120ms ease;
}

/* ── Pinned panel (right column) ─────────────────────────────────────────── */

#pinned-panel {
    padding: 0;
}

.panel-header {
    margin-bottom: 2px;
}

.panel-title {
    color: rgba(255, 255, 255, 0.90);
    font-size: 14px;
    font-weight: bold;
}

.panel-sep {
    background-color: rgba(255, 255, 255, 0.06);
    margin-left: 0;
    margin-right: 0;
}

#add-section-btn {
    background-color: transparent;
    border: none;
    border-radius: 6px;
    padding: 3px 6px;
    min-width: 0;
    color: rgba(255, 255, 255, 0.40);
    transition: background-color 120ms ease, color 120ms ease;
}

#add-section-btn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    color: rgba(255, 255, 255, 0.90);
}

.section-header {
    margin-bottom: 2px;
    margin-top: 4px;
}

.section-name-label {
    color: rgba(255, 255, 255, 0.38);
    font-size: 10px;
    font-weight: bold;
}

/* Drag handle (⠿ grip icon in section header) */
.drag-handle {
    padding: 0 2px;
}

.drag-handle label {
    color: rgba(255, 255, 255, 0.22);
    font-size: 13px;
    transition: color 120ms ease;
}

.drag-handle:hover label {
    color: rgba(255, 255, 255, 0.70);
}

/* Source tile dimmed while it is being dragged */
flowboxchild.dragging {
    opacity: 0.30;
}

/* Drop-position indicator: bright vertical bar to the left of the target tile.
   border-left is inside the homogeneous allocation so it doesn't shift layout. */
flowboxchild.drop-before {
    border-left: 3px solid rgba(255, 255, 255, 0.90);
    padding-left: 1px;
    transition: none;
}

/* Preferences dialog section header */
.pref-section-header {
    font-weight: bold;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.55);
    margin-top: 4px;
}

/* Visual feedback when dragging a tile over a section's FlowBox */
.tile-drop-target {
    border-radius: 12px;
    border: 1px dashed rgba(255, 255, 255, 0.40);
    background-color: rgba(255, 255, 255, 0.05);
}

/* Visual feedback when dragging a section over another section */
.section-drop-target {
    border-top: 2px solid rgba(255, 255, 255, 0.55);
    border-radius: 10px 10px 0 0;
}

#section-menu-btn {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 2px 5px;
    min-width: 0;
    color: rgba(255, 255, 255, 0.25);
    transition: background-color 100ms ease, color 100ms ease;
}

#section-menu-btn:hover {
    background-color: rgba(255, 255, 255, 0.10);
    color: rgba(255, 255, 255, 0.80);
}

.empty-hint {
    color: rgba(255, 255, 255, 0.25);
    font-size: 12px;
    padding: 30px 20px;
}

.add-section-hint {
    background-color: transparent;
    border: 1px dashed rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.18);
    padding: 8px 14px;
    margin-top: 8px;
    transition: background-color 150ms ease, color 150ms ease, border-color 150ms ease;
}

.add-section-hint:hover {
    background-color: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.35);
    color: rgba(255, 255, 255, 0.70);
}

/* ── App tiles (used in pinned panel) ────────────────────────────────────── */

flowboxchild {
    border-radius: 14px;
    padding: 10px 6px;
    background-color: transparent;
    outline: none;
    transition: background-color 180ms ease;
}

flowboxchild.hovered {
    background-color: rgba(255, 255, 255, 0.13);
    transition: background-color 80ms ease;
}

flowboxchild.pressed {
    background-color: rgba(255, 255, 255, 0.28);
    transition: background-color 40ms ease;
}

flowboxchild:selected,
flowboxchild:focus {
    outline: none;
    box-shadow: none;
    background-color: transparent;
}

.app-label {
    color: rgba(255, 255, 255, 0.65);
    font-size: 11px;
    transition: color 180ms ease;
}

flowboxchild.hovered .app-label {
    color: rgba(255, 255, 255, 1.0);
    transition: color 80ms ease;
}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */

scrolledwindow, viewport {
    background-color: transparent;
}

scrollbar {
    background-color: transparent;
    border: none;
}

scrollbar slider {
    background-color: rgba(255, 255, 255, 0.18);
    border-radius: 4px;
    min-width: 4px;
    min-height: 4px;
}

scrollbar slider:hover {
    background-color: rgba(255, 255, 255, 0.32);
}

"""


_bg_provider     = None
_border_provider = None


def apply_border_css(s) -> None:
    global _border_provider
    hex_col = s.border_color.lstrip("#")
    r = int(hex_col[0:2], 16)
    g = int(hex_col[2:4], 16)
    b = int(hex_col[4:6], 16)
    if s.border_width > 0:
        border = f"{s.border_width}px solid rgba({r}, {g}, {b}, {s.border_alpha:.3f})"
    else:
        border = "none"
    css = f"#start-container {{ border: {border}; }}".encode()
    if _border_provider is None:
        _border_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            _border_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
    _border_provider.load_from_data(css)


def apply_background_css(s) -> None:
    """Inject the container background color from settings (independent of Plank).
    Safe to call multiple times — reuses the same provider."""
    global _bg_provider
    hex_col = s.background_color.lstrip("#")
    r = int(hex_col[0:2], 16)
    g = int(hex_col[2:4], 16)
    b = int(hex_col[4:6], 16)
    bg  = f"rgba({r}, {g}, {b}, {s.background_opacity:.2f})"
    css = f"#start-container {{ background-color: {bg}; }}".encode()
    if _bg_provider is None:
        _bg_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            _bg_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
        )
    _bg_provider.load_from_data(css)


def apply_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode())
    Gtk.StyleContext.add_provider_for_screen(
        Gdk.Screen.get_default(),
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
    )

    from .settings import settings as _s
    apply_background_css(_s)
    apply_border_css(_s)
    apply_size_css(_s)


_size_provider = None


def apply_size_css(s) -> None:
    """Inject font-size overrides for the tile and list labels.
    Called once on startup and again whenever preferences change."""
    global _size_provider
    css = (
        f".app-label {{ font-size: {s.tile_font_size}px; }}\n"
        f".list-app-name {{ font-size: {s.list_font_size}px; }}\n"
        f".section-name-label {{ font-size: {s.section_label_font_size}px; }}\n"
    ).encode()
    if _size_provider is None:
        _size_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            _size_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 2,
        )
    _size_provider.load_from_data(css)
