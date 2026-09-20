"""Read-only terminal location browser. Selection never changes image files."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


def linked(path: Path) -> bool:
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


def starting_directory(root: Path | None = None) -> Path:
    if root and root.is_dir():
        return root
    pictures = Path.home() / "Pictures"
    return pictures if pictures.is_dir() else Path.home()


def application_directory() -> Path:
    from ..store import application_directory as shared_application_directory
    return shared_application_directory()


def validate_workspace(path: Path) -> Path:
    from .service import Request, root_of
    path = path.expanduser().absolute()
    return root_of(Request("list", path))


@dataclass
class Picker:
    directory: Path
    multiple: bool = False
    selected: list[Path] = field(default_factory=list)
    error: str = ""

    def rows(self) -> list[dict[str, str | Path | bool]]:
        rows: list[dict[str, str | Path | bool]] = [{"kind": "accept", "title": f"Continue with {len(self.selected)} selected" if self.multiple else "Use this folder"},
                {"kind": "parent", "title": "..  Parent folder", "path": self.directory.parent}]
        try:
            # Directory-entry attributes avoid statting every media file merely
            # to browse folders, especially expensive on large/network libraries.
            children: list[tuple[bool, Path]] = []
            with os.scandir(self.directory) as entries:
                for entry in entries:
                    if entry.name in {".riposte", ".shroud"}:
                        continue
                    directory = entry.is_dir(follow_symlinks=False)
                    if not directory and not (self.multiple and entry.is_file(follow_symlinks=False)):
                        continue
                    path = Path(entry.path)
                    if not entry.is_symlink() and not linked(path):
                        children.append((directory, path))
            for directory, path in sorted(children, key=lambda item: (not item[0], item[1].name.casefold())):
                rows.append({"kind": "directory" if directory else "file", "title": path.name,
                             "path": path, "selected": path in self.selected})
            self.error = ""
        except OSError:
            self.error = "Cannot read this folder. Choose its parent or another location."
        return rows

    def enter(self, directory: Path) -> None:
        if linked(directory) or not directory.is_dir():
            self.error = "Choose an existing folder; linked folders are not followed."
            return
        self.directory = directory.absolute()
        self.error = ""

    def toggle(self, path: Path) -> None:
        if path in self.selected:
            self.selected.remove(path)
        else:
            self.selected.append(path)


def locations() -> list[dict[str, str | Path | bool]]:
    paths = [Path.home(), Path.home() / "Pictures"]
    paths += [Path(f"{letter}:/") for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"] if os.name == "nt" else [Path("/")]
    return [{"kind": "directory", "title": str(p), "path": p} for p in dict.fromkeys(paths) if p.is_dir()]
