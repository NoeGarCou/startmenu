# CLAUDE.md — Custom App Launcher ("PillMenu")

## What we're building

A custom application launcher for **Linux Mint Cinnamon**, designed to pair with a
floating Plank Reloaded dock. It opens as a **bottom-center floating window** that sits
just above the dock, shows installed apps as a **grid of icons with a search box on top**,
and launches an app when clicked. Think of it as a lightweight, self-styled app menu —
not tethered to a specific dock icon, just anchored to the bottom-center of the screen.

The whole point of this project is **full control over the look** so it matches an
existing themed desktop (dark "pill" aesthetic, rounded corners, Tela-circle icons).

## Hard scope boundaries (read before coding)

This is **v1**. Keep it small and working. Do NOT add features beyond this list without
asking. The temptation to gold-plate this is the main risk.

IN scope for v1:
- A single bottom-center floating window.
- Search box at the top, app grid below.
- Reads installed apps from `.desktop` files.
- Click an app to launch it; window closes after launching.
- Type in the search box to filter the grid live.
- Open via a global hotkey AND via a pinned Plank launcher (both trigger the same thing).
- Toggle behaviour: if already open, the trigger closes it.
- Closes on Escape key and on focus-loss (clicking away).
- Dark, rounded, themed styling via embedded CSS.

OUT of scope for v1 (note them, do not build them):
- Pinning/favorites, recent apps, categories/folders.
- Animations beyond a simple fade (no "rising from the dock icon" — explicitly not doing this).
- Power/settings buttons, user avatar, etc.
- Multi-monitor positioning logic (assume single primary monitor for now).
- Keyboard arrow-key navigation of the grid (nice-to-have for v2).

## Target environment

- OS: Linux Mint (Cinnamon desktop), Ubuntu 24.04 "noble" base.
- Display server: X11 (NOT Wayland) — Cinnamon runs X11. Positioning code can rely on X11.
- Language: **Python 3** (system python3, 3.12.x).
- GUI toolkit: **GTK 3** via PyGObject (`gi`). GTK3 is already installed system-wide on Mint.
  - Import pattern:
    ```python
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk, GdkPixbuf, Gio, GLib
    ```
- The dev environment is VS Code. Assume the user will run the script with `python3 pillmenu.py`.

## Positioning math (the key detail)

The launcher window is positioned bottom-center with a fixed bottom offset that clears the
Plank dock. This is deterministic — no need to query Plank's window geometry.

Bottom offset (pixels from screen bottom to the launcher's bottom edge) is the sum of:
- Plank gap-size: **10px** (the floating gap under the dock)
- Plank dock height: roughly **icon-size (40) + theme padding (~16)** ≈ **56px**
- Breathing room so the menu isn't glued to the dock: **~25px**

So a reasonable constant is **BOTTOM_OFFSET ≈ 90px**. Make this a named constant at the top
of the file so it's trivially tweakable. The user may adjust it after seeing it on screen.

Horizontal: center the window on the primary monitor's width.
Window size: pick a sensible fixed size for v1 (e.g. 640x520) and center horizontally.

Use the monitor geometry from GdkScreen/GdkMonitor to compute center and bottom. On X11,
`Gtk.Window.move(x, y)` works for absolute positioning — use it. Set the window type hint to
DIALOG or UTILITY so it floats and doesn't get a taskbar entry. Consider
`set_keep_above(True)` so it sits above other windows.

## Reading installed apps

Use Gio for this — do NOT hand-parse .desktop files; Gio does it correctly including
locale-aware names, NoDisplay handling, and icon resolution.

```python
from gi.repository import Gio
apps = Gio.AppInfo.get_all()          # list of GAppInfo
# filter: skip ones where should_show() is False (handles NoDisplay/OnlyShowIn correctly)
visible = [a for a in apps if a.should_show()]
# each app: a.get_display_name(), a.get_icon(), a.launch([], None)
```

For icons: `app.get_icon()` returns a GIcon. Render it with a Gtk.Image via
`Gtk.Image.new_from_gicon(icon, Gtk.IconSize.DIALOG)` — this respects the active icon theme,
so it'll automatically use the user's Tela-circle icons. Do not try to load icon files by
path manually; let GTK's icon theme resolve them.

Sort the visible apps alphabetically by display name for the grid.

## Search / filtering

- A Gtk.SearchEntry (or Gtk.Entry) at the top.
- On every "changed" signal, filter the app list case-insensitively by substring match on
  the display name. Optionally also match the executable/keywords, but name-match is fine for v1.
- Re-render the grid with the filtered subset. Keep it simple: clear and rebuild the grid
  container, or use a Gtk.FlowBox with a filter function (FlowBox is the cleaner choice —
  it has built-in `set_filter_func`).
- Grab keyboard focus on the search entry when the window opens, so the user can type immediately.

## Layout

- Use a Gtk.FlowBox inside a Gtk.ScrolledWindow for the app grid (FlowBox handles wrapping
  and is filter-friendly).
- Each grid item: a vertical box with the icon on top and the app name label below, in a
  Gtk.FlowBoxChild. Make items a uniform size.
- Search entry pinned above the scrolled grid in a vertical Gtk.Box.

## Launching

- On item activation (click or Enter): call `app_info.launch([], None)`, then hide/close the
  launcher window. Wrap in try/except and print errors to stderr; don't crash on a bad launch.

## Open / close / toggle behaviour

The launcher should behave like a toggle and be cheap to invoke. Two trigger paths, same result:

1. **Global hotkey:** Cinnamon handles global hotkeys natively. The plan is to bind a custom
   keyboard shortcut in Cinnamon (System Settings > Keyboard > Shortcuts > Custom) that runs a
   command. So the app needs a way to be "toggled" from the command line.

2. **Plank launcher:** A pinned .desktop whose Exec runs the same toggle command.

To support toggling from a one-shot command invocation, implement a **single-instance** model:
- On launch, try to talk to an already-running instance (use Gtk.Application with
  `Gio.ApplicationFlags.HANDLES_COMMAND_LINE` and the built-in single-instance support, or a
  simple approach: a Gtk.Application with a unique application_id; the second invocation's
  `do_activate` toggles visibility of the existing window).
- Gtk.Application with a fixed `application_id` (e.g. "org.nlinux.PillMenu") gives
  single-instance for free: the first run starts the app, subsequent runs call `activate` on the
  existing instance. Use the `activate` handler to toggle the window (show if hidden, hide if visible).

This way the hotkey and the Plank icon both just run `python3 pillmenu.py` (or an installed
command), and the running instance toggles. Cold start on first invocation is fine.

- Escape key closes (hides) the window.
- Focus-out event (`focus-out-event`) hides the window, so clicking away dismisses it — but make
  this toggle-able via a constant, because focus-out can be annoying during development.

## Styling

- Embed CSS via Gtk.CssProvider loaded onto the default screen.
- Aesthetic to match the user's desktop:
  - Window/background: dark, approximately `rgba(28, 28, 40, 0.96)`.
  - Rounded window corners: border-radius ~18px on the top-level container. (Note: true rounded
    window corners on X11 need the window to be RGBA-visual + app-painted; for v1 it's acceptable
    to round an inner container and give the window a matching dark background. Document this
    limitation in a comment.)
  - Search entry: dark, subtle border, rounded.
  - Grid item hover: subtle light highlight `rgba(255,255,255,0.10)`, rounded corners ~14px.
  - Text: near-white `rgba(255,255,255,0.9)`.
- Keep all CSS in one string constant at the top of the file for easy tweaking.

## File structure for v1

Single file is fine: `pillmenu.py`. If it grows, split later. Keep tweakable constants grouped
at the very top:

```python
BOTTOM_OFFSET = 90      # px above screen bottom (clears Plank dock)
WINDOW_WIDTH  = 640
WINDOW_HEIGHT = 520
ICON_SIZE     = Gtk.IconSize.DIALOG
HIDE_ON_FOCUS_LOSS = True
APP_ID = "org.nlinux.PillMenu"
```

## Integration steps (document these in a README section, the user will do them manually)

1. Run directly to test: `python3 pillmenu.py`
2. Pin to Plank: create `~/.local/share/applications/pillmenu.desktop` with
   `Exec=python3 /full/path/to/pillmenu.py`, give it an icon, then drag it from the Cinnamon
   menu onto Plank.
3. Global hotkey: System Settings > Keyboard > Shortcuts > Custom Shortcuts > add a shortcut
   running `python3 /full/path/to/pillmenu.py`, bind it to a key.

## Coding guidance for the assistant

- Write clear, commented code. This is partly a learning project for the user.
- Prefer the simple, robust GTK idiom over clever tricks.
- Be explicit in comments about anything that is an X11/Cinnamon-specific assumption, or any
  spot that is a known limitation (e.g. rounded window corners, focus-out quirks).
- Do not silently expand scope. If something in v1 turns out to need a v2 feature to work well,
  call it out rather than building the v2 feature.
- Test mentally against the single-instance toggle flow: first invocation opens; second
  invocation (from hotkey or Plank) should toggle the same window, not spawn a second.
