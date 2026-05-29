"""
Persistent pinned-apps data model.

Stored in ~/.config/startmenu/pinned.json as a list of user-defined sections,
each containing an ordered list of desktop app IDs.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

_PINNED_PATH = Path.home() / ".config/startmenu/pinned.json"
_OLD_PINNED  = Path.home() / ".config/pillmenu/pinned.json"

# One-time migration from pillmenu config dir.
if not _PINNED_PATH.exists() and _OLD_PINNED.exists():
    import shutil
    _PINNED_PATH.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_OLD_PINNED, _PINNED_PATH)


@dataclass
class Section:
    id: str
    name: str
    apps: list[str] = field(default_factory=list)  # desktop app IDs


@dataclass
class PinnedData:
    sections:      list[Section]  = field(default_factory=list)
    folder_labels: dict[str, str] = field(default_factory=dict)  # folder_id → label override
    folder_icons:  dict[str, str] = field(default_factory=dict)  # folder_id → icon name override

    # ── Persistence ───────────────────────────────────────────────────

    def save(self) -> None:
        _PINNED_PATH.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {
            "sections": [
                {"id": s.id, "name": s.name, "apps": s.apps}
                for s in self.sections
            ]
        }
        if self.folder_labels:
            data["folder_labels"] = self.folder_labels
        if self.folder_icons:
            data["folder_icons"] = self.folder_icons
        _PINNED_PATH.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls) -> PinnedData:
        try:
            raw = json.loads(_PINNED_PATH.read_text())
            return cls(
                sections=[
                    Section(id=s["id"], name=s["name"], apps=s.get("apps", []))
                    for s in raw.get("sections", [])
                ],
                folder_labels=raw.get("folder_labels", {}),
                folder_icons=raw.get("folder_icons", {}),
            )
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return cls()

    # ── Section management ────────────────────────────────────────────

    def add_section(self, name: str) -> Section:
        section = Section(id=str(uuid.uuid4()), name=name)
        self.sections.append(section)
        self.save()
        return section

    def remove_section(self, section_id: str) -> None:
        self.sections = [s for s in self.sections if s.id != section_id]
        self.save()

    def rename_section(self, section_id: str, name: str) -> None:
        for s in self.sections:
            if s.id == section_id:
                s.name = name
                self.save()
                return

    # ── Pin / unpin / move ────────────────────────────────────────────

    def pin(self, app_id: str, section_id: str) -> None:
        for s in self.sections:
            if s.id == section_id and app_id not in s.apps:
                s.apps.append(app_id)
                self.save()
                return

    def unpin(self, app_id: str, section_id: str) -> None:
        for s in self.sections:
            if s.id == section_id:
                s.apps = [a for a in s.apps if a != app_id]
                self.save()
                return

    def move(self, app_id: str, from_id: str, to_id: str) -> None:
        for s in self.sections:
            if s.id == from_id:
                s.apps = [a for a in s.apps if a != app_id]
        for s in self.sections:
            if s.id == to_id and app_id not in s.apps:
                s.apps.append(app_id)
        self.save()

    # ── Folder label overrides ────────────────────────────────────────

    def set_folder_label(self, folder_id: str, label: str | None) -> None:
        if label:
            self.folder_labels[folder_id] = label
        else:
            self.folder_labels.pop(folder_id, None)
        self.save()

    def set_folder_icon(self, folder_id: str, icon_name: str | None) -> None:
        if icon_name:
            self.folder_icons[folder_id] = icon_name
        else:
            self.folder_icons.pop(folder_id, None)
        self.save()

    # ── Queries ───────────────────────────────────────────────────────

    def is_pinned(self, app_id: str) -> bool:
        return any(app_id in s.apps for s in self.sections)

    def get_section(self, section_id: str) -> Section | None:
        return next((s for s in self.sections if s.id == section_id), None)


# Module-level singleton — import this directly
pinned_data = PinnedData.load()
