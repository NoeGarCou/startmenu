"""
FolderInfo / FileInfo — lightweight objects that mimic the Gio.AppInfo
interface for pinned folder and file tiles.  AppItem and the drag/drop
system only call get_id(), get_display_name(), get_icon(), and launch().
"""
import os
import sys

import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio

_FOLDER_PREFIX = "folder://"
_FILE_PREFIX   = "pinfile://"

# ── Folder helpers ────────────────────────────────────────────────────────────

def make_id(path: str) -> str:           # backward-compat alias
    return f"{_FOLDER_PREFIX}{path}"

def path_from_id(folder_id: str) -> str:
    return folder_id[len(_FOLDER_PREFIX):]

def is_folder_id(app_id: str) -> bool:
    return app_id.startswith(_FOLDER_PREFIX)

# ── File helpers ──────────────────────────────────────────────────────────────

def make_file_id(path: str) -> str:
    return f"{_FILE_PREFIX}{path}"

def file_path_from_id(file_id: str) -> str:
    return file_id[len(_FILE_PREFIX):]

def is_file_id(app_id: str) -> bool:
    return app_id.startswith(_FILE_PREFIX)


class FolderInfo:
    """Wraps a filesystem path so it can be pinned and shown as a tile."""

    def __init__(self, path: str, label: str | None = None, icon_name: str | None = None):
        self._path      = path
        self._label     = label      # explicit override; None = use Gio / basename
        self._icon_name = icon_name  # explicit icon override; None = use Gio
        self._ginfo     = None       # lazy-loaded GFileInfo

    def _file_info(self):
        """Query Gio once for display-name + icon; cache the result."""
        if self._ginfo is None:
            try:
                self._ginfo = Gio.File.new_for_path(self._path).query_info(
                    "standard::display-name,standard::icon",
                    Gio.FileQueryInfoFlags.NONE,
                    None,
                )
            except Exception:
                self._ginfo = False   # sentinel: don't retry
        return self._ginfo or None

    def get_id(self) -> str:
        return make_id(self._path)

    def get_display_name(self) -> str:
        if self._label:
            return self._label
        info = self._file_info()
        if info:
            name = info.get_display_name()
            if name:
                return name
        # Fallback: basename (handles paths Gio can't stat).
        name = os.path.basename(self._path.rstrip("/"))
        return name or self._path

    def get_icon(self):
        if self._icon_name:
            return Gio.ThemedIcon.new(self._icon_name)
        # Gio knows the right icon for every path: "computer" for /,
        # "user-home" for ~, "folder-documents" for ~/Documents, etc.
        info = self._file_info()
        if info:
            icon = info.get_icon()
            if icon:
                return icon
        return Gio.ThemedIcon.new("folder")

    def launch(self, _files, _context) -> bool:
        try:
            uri = Gio.File.new_for_path(self._path).get_uri()
            Gio.AppInfo.launch_default_for_uri(uri, None)
            return True
        except Exception as exc:
            print(f"StartMenu: {exc}", file=sys.stderr)
            return False


class FileInfo(FolderInfo):
    """Like FolderInfo but for an individual file. Uses pinfile:// prefix."""

    def get_id(self) -> str:
        return make_file_id(self._path)
